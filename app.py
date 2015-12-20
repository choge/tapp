import os
import os.path
import hashlib
import json
import logging
import numpy
import smtplib
import email.mime.text
import concurrent

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.gen
import psycopg2
import momoko

import predictor

tornado.options.define('port',
                       default=8080,
                       help='run on the given port',
                       type=int)

class BaseHandler(tornado.web.RequestHandler):
    """A Base class (for registering the db as property"""
    @property
    def db(self):
        return self.application.db

    @property
    def dataset_maker(self):
        return self.application.dataset_maker

    @property
    def mail(self):
        return self.application.mail_connection

    @property
    def executor(self):
        return self.application.executor

class TopPageHandler(BaseHandler):
    """TopPageHandler  """

    def get(self):
        self.render('index.html',
                    page_title='TA Protein Predictor - top')


class QueryHandler(BaseHandler):
    """QueryHandler  handles queries from the top page, and write them to DB.

    Every query is stored in query table using hash-value of the string as
    primary key for the table. This aims caching same queries to avoid
    heavy calculations.
    """

    select_statement = "SELECT 1 FROM queries WHERE id = %s;"
    insert_statement = "INSERT INTO queries (id, seq, created_date) values (%s, %s, current_date);"

    @tornado.gen.coroutine
    def post(self):
        """requires a set of fasta sequences, and returns the result

        @param  query (as a POST message). It should be ACII string, and formatted as FASTA.
        @return  this handler redirects users to result page, where the results
                 will be shown in response to another request to PredictHandler.
        """
        query = self.get_argument('query')

        # register the query
        identifier = hashlib.sha256(query.encode('utf-8')).hexdigest()
        try:
            cursor = yield self.db.execute(self.select_statement,
                                            (identifier, ))
            logging.info("try to retrieve the cached query: %s", self.select_statement % (identifier))
            # if not registered, insert the data
            if len(cursor.fetchall()) == 0:
                cursor = yield self.db.execute(self.insert_statement,
                                         (identifier, query,))
                logging.info("register the query: %s", self.insert_statement % (identifier, '**',))
        except (psycopg2.Warning, psycopg2.Error) as error:
            self.write(str(error))
        else:
            logging.debug('inserted query data (id: %s)', identifier)

        self.redirect("./result/{0}".format(identifier), permanent=True)


class PredictHandler(BaseHandler):
    """PredictHandler  handles requests from the result page and returns the result of prediction.

    The Javascript function in the result page calls this handler, and return the result
    in JSON format.
    TODO: Long polling or WebSockets should be used to avoid redundunt calculations."""
    select_query = "SELECT id, seq FROM queries WHERE id = %s;"
    select_result = "SELECT id, result FROM results where id = %s;"
    insert_result = "INSERT INTO results (id, result, mail_address, calculated) " \
                    + "values (%s, null, null, null);"
    update_result = "UPDATE results SET result = %s, calculated = current_date " \
                    + "where id = %s;"
    select_mail_address = "SELECT mail_address FROM results where id = %s"

    @tornado.gen.coroutine
    def get(self, query_id):
        """Handles GET request from the result page.

        @param query_id  as a GET parameter, which should be the hash-key for the query.
        @returns  prediction result in JSON format.
        """
        try:
            # fetch the cached result
            cursor_r = yield self.db.execute(self.select_result,
                                     (query_id, ))
            results = cursor_r.fetchall()

            if len(results) > 0 and results[0][1] is not None:
                # results[0][1] should be the predicted result,
                # so retruns the result if found.
                logging.info('Found the cached result. %s' % (query_id,))
                self.write(results[0][1])
                #
                # codes below possibly make the result never back
                # (in case previous prediction request hangs or terminated)
                #elif len(results) > 0 and results[0][1] is None:
                # found the result, but it might be still under calculation.
                #logging.info('Found the result record, but still under calculation')
            else:

                # retrieve query
                cursor_q = yield self.db.execute(self.select_query,
                                         (query_id, ))
                queries = cursor_q.fetchall()
                if len(queries) == 0 or len(queries[0]) == 0:
                    logging.error("No query found.")
                    # TODO: should forward to some cool error page.
                query = cursor_q.fetchall()[0][1]
                logging.info('retrieve the query : %s', self.select_query % (query_id,))

                # insert blank data
                if len(results) == 0:
                    yield self.db.execute(self.insert_result,
                                    (query_id, ))
                    logging.debug('inserted blank result data (id: %s)', query_id)

                # create object and predict
                query_data = self.dataset_maker.read_from_string(query)
                # perform prediction
                logging.debug('start calculation')
                predicted = yield self.executor.submit(
                        self.application.myhmm.predict,
                        query_data, True)
                logging.debug('TA protein model prediction completed')
                predicted_mp = yield self.executor.submit(
                        self.application.mphmm.predict,
                        query_data, False)
                logging.debug('Multi-pass model prediction completed')

                predicted_json = json.dumps(self.convert_numpy_types(predicted, predicted_mp))
                logging.info('calculation finished: %s', predicted_json[:100] + '...')

                # after calculation has been finished, update the table
                yield self.db.execute(self.update_result,
                                (predicted_json, query_id,))
                logging.info('updated the result: %s',
                        self.update_result % (predicted_json[:100] + '...', query_id,))

                # see if an e-mail address has been registered or not
                cursor_m = yield self.db.execute(self.select_mail_address,
                                           (query_id,))
                logging.info('See if there are email address registered: %s',
                        self.select_mail_address % (query_id, ))
                mail_address = cursor_m.fetchall()

                if len(mail_address) > 0 and mail_address[0][0] is not None:  # there are mail address registered
                    logging.info('found the email address. Sending the mail that notifies completion of the prediction (to %s).', str(mail_address))
                    self.send_completion_mail(query_id, mail_address[0][0])

                self.write(predicted_json)
        except (psycopg2.Warning, psycopg2.Error) as error:
            self.write(str(error))


    def async_predict(self, myhmm, dataset, reverse=True, callback=None):
        """Async wrapper for predict.
        Though usually myhmm.predict() doesn't take much time,
        make it asynchrounous would be better as for performance."""
        callback(myhmm.predict(dataset, reverse))

    def convert_numpy_types(self, predicted, predicted_mp):
        """As numpy types such as 'numpy.int64' cannot be converted into
        JSON format, so make these values into native python values.

        @param predicted  is a dictionary of the predicted result.
        predicted
        +[seq_id]
         +['path'] : str, decoded path
         +['pathnum'] : list of numpy.int64
         +['likelihood'] : numpy.float64
         +['omega'] : list of numpy.float64. """
        new_result = {}
        for seq_id, dic in predicted.items():
            converted = {}
            converted['pathnum'] = [i.item() for i in dic['pathnum']]
            converted['omega'] = [i.item() for i in dic['omega']]
            converted['likelihood'] = dic['likelihood'].item()
            converted['path'] = dic['path']
            converted['likelihood_mp'] = predicted_mp[seq_id]['likelihood'].item()
            converted['score'] = (converted['likelihood'] - converted['likelihood_mp']) / len(dic['path'])
            converted['has_tmd'] = 'HHHHHHHHHHHHHHH' in dic['path']
            converted['is_ta'] = converted['score'] >= self.application.threshold
            new_result[seq_id] = converted
        return new_result

    @tornado.gen.coroutine
    def send_completion_mail(self, query_id, mail_address):
        """send an email that notifies the prediction has been completed."""
        body = """Dear user,

        Thank you for using our TA Protein Predictor.

        Your prediction at TA Protein Predictor has been completed.
        Please visit the following URL to see the result.
        {0}

        Thanks,

        TA Protein Predictor@bilab""".format(
            'http://' + self.application.HOSTNAME + '/result/' + query_id)
        msg = email.mime.text.MIMEText(body)
        msg['from'] = 'tapp@bi.a.u-tokyo.ac.jp'
        msg['to'] = mail_address
        msg['reply-to'] = 'choge@bi.a.u-tokyo.ac.jp'
        msg['subject'] = 'TA Protein Prediction finished (ID:' + query_id + ')'

        self.mail.sendmail(msg['from'], [msg['to']], msg.as_string())


class ResultPageHandler(BaseHandler):
    """ResultPageHandler"""
    statement = "SELECT id, seq FROM queries WHERE id = %s;"

    @tornado.gen.coroutine
    def get(self, result_id):
        """show the result page, which is stored in DB."""
        try:
            cursor = yield self.db.execute(self.statement, (result_id, ))
        except (psycopg2.Warning, psycopg2.Error) as error:
            self.write(str(error))
        else:
            query = cursor.fetchall()[0][1]
            logging.info('selected the statement')

        # create query object and predict
        query_data = self.dataset_maker.read_from_string(query)

        self.render('result.html',
                    query_id=result_id,
                    query_data=query_data,
                    page_title="TA Protein Predictor : prediction result")

class EmailSendHandler(BaseHandler):
    """EmailSendHandler"""
    statement = "UPDATE results SET mail_address = %s where id = %s"

    @tornado.gen.coroutine
    def post(self, query_id):
        mail_address = self.get_argument('email')

        try:
            yield self.db.execute(self.statement,
                            (mail_address, query_id,))
        except (psycopg2.Warning, psycopg2.Error) as error:
            self.write(str(error))

        self.send_registeration_mail(query_id, mail_address)

    def send_registeration_mail(self, query_id, mail_address):
        """send an email that notifies the prediction has been completed."""
        body = """Dear user,

        Thank you for using our TA Protein Predictor.

        Your prediction at TA Protein Predictor has been started.
        Please visit the following URL to see the result after a while.
        {0}

        Thanks,

        TA Protein Predictor@bilab""".format(
            'http://' + self.application.HOSTNAME + '/result/' + query_id)
        msg = email.mime.text.MIMEText(body)
        msg['from'] = 'tapp@bi.a.u-tokyo.ac.jp'
        msg['to'] = mail_address
        msg['reply-to'] = 'choge@bi.a.u-tokyo.ac.jp'
        msg['subject'] = 'TA Protein Prediction finished (ID:' + query_id + ')'

        try:
            self.mail.sendmail(msg['from'], [msg['to']], msg.as_string())
        except smtplib.SMTPServerDisconnected as error:
            logging.info('mail connection has been disconnected. Try to re-connect.')
            self.application.mail_connectino = smtplib.SMTP('localhost')
            self.mail.sendmail(msg['from'], [msg['to']], msg.as_string())


class Application(tornado.web.Application):
    """Web app"""
    HOSTNAME = 'tenuto.bi.a.u-tokyo.ac.jp/tapp'
    callbacks = {}

    def __init__(self, ioloop):
        # handlers bind paths and handlers
        handlers = [(r'/tapp/', TopPageHandler),
                    (r'/tapp/predict', QueryHandler),
                    (r'/tapp/predict/([\w\-]+)', PredictHandler),
                    (r'/tapp/result/([\w\-]+)', ResultPageHandler),
                    (r'/tapp/mail/([\w\-]+)', EmailSendHandler)]

        # Postgresql, utils, mails
        self.db = momoko.Pool(dsn = 'dbname=tapp user=tapp password=tapp'
                                    + ' host=localhost port=5432',
                              size = 1,
                              ioloop = ioloop)

        self.dataset_maker = predictor.FastaDataSetMaker()
        self.mail_connection = smtplib.SMTP('localhost')
        self.executor = concurrent.futures.ThreadPoolExecutor(10)

        # paths
        current_file_path = os.path.dirname(__file__)
        template_path = os.path.join(current_file_path, 'templates')
        static_path = os.path.join(current_file_path, 'static')

        # Threshold which determines the prediction result
        # whether the query is a TA protein or not.
        self.threshold = -0.016722298135034733
        self.myhmm = predictor.MyHmmPredictor(
                filename=os.path.join(
                    current_file_path, 'modelsFinal/ta4.xml'))
        self.myhmm.set_decoder('TTHHHHHHHHHHHHHHHHHHHHHHHHHCCCCCGTT')
        self.mphmm = predictor.MyHmmPredictor(
                filename=os.path.join(
                    current_file_path, 'modelsFinal/mp.xml'))
        self.mphmm.set_decoder('SSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSGLLLLLLLLLLLLLLLLLLLLCCCCCHHHHHHHHHHHHHHHHHHHHHHHHH')
        tornado.web.Application.__init__(self,
                handlers,
                template_path=template_path,
                static_path=static_path,
                static_url_prefix='/tapp/static/',
                debug=True)


if __name__ == '__main__':
    tornado.options.parse_command_line()
    # retreive IOLoop object
    ioloop = tornado.ioloop.IOLoop.instance()
    app = Application(ioloop)

    # for momoko
    future = app.db.connect()
    ioloop.add_future(future, lambda f: ioloop.stop())
    ioloop.start()
    future.result()

    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(tornado.options.options.port)
    ioloop.start()
