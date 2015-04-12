import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.gen
import predictor
import os
import os.path

from tornado.options import define, options

define('port', default=8080, help='run on the given port', type=int)

class TopPageHandler(tornado.web.RequestHandler):
    """TopPageHandler  """

    def get(self):
        self.render('index.html')


class QueryHandler(tornado.web.RequestHandler):
    """QueryHandler"""

    def post(self):
        """requires a set of fasta sequences, and returns the result"""
        query = self.get_argument('query')
        dataset_maker = predictor.FastaDataSetMaker()
        query_data = dataset_maker.read_from_string(query)
        myhmm = predictor.MyHmmPredictor(
                filename=os.path.join(
                    os.path.dirname(__file__), 'modelsFinal/ta4.xml'))
        myhmm.set_decoder('TTHHHHHHHHHHHHHHHHHHHHHHHHHCCCCCGTT')
        # predicted = yield tornado.gen.Task(myhmm.predict, query_data)
        predicted = myhmm.predict(query_data)
        
        self.write(str(predicted))

class ResultPageHandler(tornado.web.RequestHandler):
    """ResultPageHandler"""

    def get(self, result_id):
        """show the result page, which is stored in DB."""
        pass

if __name__ == '__main__':
    tornado.options.parse_command_line()
    current_file_path = os.path.dirname(__file__)
    app = tornado.web.Application(
            handlers=[
                (r'/', TopPageHandler),
                (r'/predict', QueryHandler),
                (r'/result/(\w+)', ResultPageHandler)
                ],
            template_path=os.path.join(current_file_path, 'templates'),
            static_path=os.path.join(current_file_path, 'static'),
            debug=True
            )
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

