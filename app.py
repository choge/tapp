import os
import os.path
import hashlib
import json
import logging
import numpy
import smtplib
import email.mime.text

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

class TopPageHandler(BaseHandler):
    """TopPageHandler  """

    def get(self):
        self.render('index.html',
                    page_title='TA Protein Predictor - top')


class QueryHandler(BaseHandler):
    """QueryHandler"""

    select_statement = "SELECT 1 FROM queries WHERE id = %s;"
    insert_statement = "INSERT INTO queries (id, seq, created_date) values (%s, %s, current_date);"

    @tornado.gen.coroutine
    def post(self):
        """requires a set of fasta sequences, and returns the result
        
        TODO: make myhmm a singleton?
        TODO: return the blank page, and register the query to DB
        (possibly mongoDB or postgreSQL??)"""
        query = self.get_argument('query')

        # register the query
        identifier = hashlib.sha256(query.encode('utf-8')).hexdigest()
        try:
            cursor = yield momoko.Op(self.db.execute, 
                                     self.select_statement, 
                                     (identifier, ))
            logging.info("try to retrieve the cached query: %s", self.select_statement % (identifier))
            # if not registered, insert the data
            if len(cursor.fetchall()) == 0:
                cursor = yield momoko.Op(self.db.execute, 
                                         self.insert_statement, 
                                         (identifier, query,))
                logging.info("register the query: %s", self.insert_statement % (identifier, '**',))
        except (psycopg2.Warning, psycopg2.Error) as error:
            self.write(str(error))
        else:
            logging.debug('inserted query data (id: %s)', identifier)

        self.redirect("./result/{0}".format(identifier), permanent=True)


class QueryAPIHandler(BaseHandler):
    """QueryAPIHandler  will return the result in JSON
    
    TODO: write"""
    select_query = "SELECT id, seq FROM queries WHERE id = %s;"
    select_result = "SELECT id, result FROM results where id = %s;"
    insert_result = "INSERT INTO results (id, result, mail_address, calculated) " \
                    + "values (%s, null, null, null);"
    update_result = "UPDATE results SET result = %s, calculated = current_date " \
                    + "where id = %s;"
    select_mail_address = "SELECT mail_address FROM results where id = %s"
    
    @tornado.gen.coroutine
    def get(self, query_id):
        """returns calculate
        
        TODO: use websockets if possible """
        try:
            # fetch the cached result
            cursor_r = yield momoko.Op(self.db.execute,
                                     self.select_result,
                                     (query_id, ))
            results = cursor_r.fetchall()
        
            if len(results) > 0 and results[0][1] is not None:
                logging.info('Found the cached result. %s' % (query_id,))
                self.write(results[0][1])
            else:

                # retrieve query
                cursor_q = yield momoko.Op(self.db.execute, 
                                         self.select_query,
                                         (query_id, ))
                # TODO: write error codes (when there are no queries)
                query = cursor_q.fetchall()[0][1]
                logging.info('retrieve the query : %s', self.select_query % (query_id,))

                # insert blank data
                if len(results) == 0:
                    yield momoko.Op(self.db.execute,
                                    self.insert_result,
                                    (query_id, ))
                    logging.debug('inserted blank result data (id: %s)', query_id)

                # create object and predict
                query_data = self.dataset_maker.read_from_string(query)
                # perform prediction
                predicted = yield tornado.gen.Task(self.async_predict, 
                        self.application.myhmm, query_data, True)
                predicted_mp = yield tornado.gen.Task(self.async_predict,
                        self.application.mphmm, query_data, False)
                
                predicted_json = json.dumps(self.convert_numpy_types(predicted, predicted_mp))
                logging.info('calculation finished: %s', predicted_json[:100] + '...')

                # after calculation has been finished, update the table
                yield momoko.Op(self.db.execute,
                                self.update_result,
                                (predicted_json, query_id,))
                logging.info('updated the result: %s', 
                        self.update_result % (predicted_json[:100] + '...', query_id,))

                # see if an e-mail address has been registered or not
                cursor_m = yield momoko.Op(self.db.execute,
                                           self.select_mail_address,
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
            cursor = yield momoko.Op(self.db.execute, self.statement, (result_id, ))
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
            yield momoko.Op(self.db.execute, 
                            self.statement,
                            (mail_address, query_id,))
        except (psycopg2.Warning, psycopg2.Error) as error:
            self.write(str(error))
        
        self.send_registeration_mail(query_id, mail_address)
    
    def send_registeration_mail(self, query_id, mail_address):
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

        try:
            self.mail.sendmail(msg['from'], [msg['to']], msg.as_string())
        except smtplib.SMTPServerDisconnected as error:
            logging.info('mail connection has been disconnected. Try to re-connect.')
            self.application.mail_connectino = smtplib.SMTP('localhost')
            self.mail.sendmail(msg['from'], [msg['to']], msg.as_string())


class Application(tornado.web.Application):
    """Web app"""
    HOSTNAME = 'tenuto.bi.a.u-tokyo.ac.jp'

    def __init__(self):
        handlers = [(r'/tapp/', TopPageHandler),
                    (r'/tapp/predict', QueryHandler),
                    (r'/tapp/predict/([\w\-]+)', QueryAPIHandler),
                    (r'/tapp/result/([\w\-]+)', ResultPageHandler),
                    (r'/tapp/mail/([\w\-]+)', EmailSendHandler)]
        self.db = momoko.Pool(dsn = 'dbname=tapp user=tapp password=tapp'
                                    + ' host=localhost port=5432',
                              size = 1)
        self.dataset_maker = predictor.FastaDataSetMaker()
        self.mail_connection = smtplib.SMTP('localhost')

        current_file_path = os.path.dirname(__file__)
        template_path = os.path.join(current_file_path, 'templates')
        static_path = os.path.join(current_file_path, 'static')

        self.threshold = -0.0084918561822501237
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
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(tornado.options.options.port)
    tornado.ioloop.IOLoop.instance().start()
