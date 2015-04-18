import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.gen
import os
import os.path
import momoko

from tornado.options import define, options

import predictor

define('port', default=8080, help='run on the given port', type=int)

class TopPageHandler(tornado.web.RequestHandler):
    """TopPageHandler  """

    def get(self):
        self.render('index.html')


class QueryHandler(tornado.web.RequestHandler):
    """QueryHandler"""

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        """requires a set of fasta sequences, and returns the result
        
        TODO: make myhmm a singleton?
        TODO: return the blank page, and register the query to DB
        (possibly mongoDB or postgreSQL??)"""
        query = self.get_argument('query')
        dataset_maker = predictor.FastaDataSetMaker()
        query_data = dataset_maker.read_from_string(query)
        
        self.render('result.html', results=predicted)

    def async_predict(self, myhmm, dataset, reverse=True, callback=None):
        """Async wrapper for predict.
        Though usually myhmm.predict() doesn't take much time, 
        make it asynchrounous would be better as for performance."""
        callback(myhmm.predict(dataset, reverse))
        

class QueryAPIHandler(tornado.web.RequestHandler):
    """QueryAPIHandler  will return the result in JSON
    
    TODO: write"""
    
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        """returns calculate"""
        query = self.get_argument('query')
        dataset_maker = predictor.FastaDataSetMaker()
        query_data = dataset_maker.read_from_string(query)
        myhmm = predictor.MyHmmPredictor(
                filename=os.path.join(
                    os.path.dirname(__file__), 'modelsFinal/ta4.xml'))
        myhmm.set_decoder('TTHHHHHHHHHHHHHHHHHHHHHHHHHCCCCCGTT')
        predicted = yield tornado.gen.Task(self.async_predict, 
                myhmm, query_data, True)
        
        self.render('result.html', results=predicted)

    def async_predict(self, myhmm, dataset, reverse=True, callback=None):
        """Async wrapper for predict.
        Though usually myhmm.predict() doesn't take much time, 
        make it asynchrounous would be better as for performance."""
        callback(myhmm.predict(dataset, reverse))

class ResultPageHandler(tornado.web.RequestHandler):
    """ResultPageHandler"""

    def get(self, result_id):
        """show the result page, which is stored in DB."""
        pass

class Application(tornado.web.Application):
    """Web app"""
    def __init__(self):
        handlers = [(r'/', TopPageHandler),
                    (r'/predict', QueryHandler),
                    (r'/result/(\w+)', ResultPageHandler)]
        db_database = 'tapp'
        db_user = 'choge'
        db_pass = 'postgres'
        db_host = 'localhost'
        db_port = 5432
        dsn = 'dbname=%s user=%s password=%s host=%s port=%s' % (
            db_database, db_user, db_pass, db_host, db_port)
        self.db = momoko.Pool(
                dsn=dsn,
                size=1,
                max_size=3,
                setsession=('SET TIME ZONE UTC')
                )
        current_file_path = os.path.dirname(__file__)
        template_path = os.path.join(current_file_path, 'templates')
        static_path = os.path.join(current_file_path, 'static')
        tornado.web.Application.__init__(self, 
                handlers, 
                template_path=template_path,
                static_path=static_path,
                debug=True)


if __name__ == '__main__':
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()