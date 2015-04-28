import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.gen
import os
import os.path
import hashlib
import shelve
import json
import numpy

from tornado.options import define, options

import predictor

define('port', default=8080, help='run on the given port', type=int)

class TopPageHandler(tornado.web.RequestHandler):
    """TopPageHandler  """

    def get(self):
        self.render('index.html',
                    page_title='TA Protein Predictor - top')


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
        identifier = hashlib.sha256(query.encode('utf-8')).hexdigest()
        self.application.db[identifier] = query_data
        
        self.redirect("result/{0}".format(identifier), permanent=True)

class QueryAPIHandler(tornado.web.RequestHandler):
    """QueryAPIHandler  will return the result in JSON
    
    TODO: write"""
    
    @tornado.gen.coroutine
    def get(self, query_id):
        """returns calculate"""
        query_data = self.application.db[query_id]
        myhmm = predictor.MyHmmPredictor(
                filename=os.path.join(
                    os.path.dirname(__file__), 'modelsFinal/ta4.xml'))
        myhmm.set_decoder('TTHHHHHHHHHHHHHHHHHHHHHHHHHCCCCCGTT')
        sphmm = predictor.MyHmmPredictor(
                filename=os.path.join(
                    os.path.dirname(__file__), 'modelsFinal/sp.xml'))
        sphmm.set_decoder('SSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSGGCCCCCHHHHHHHHHHHHHHHHHHHHHHHHH')
        mphmm = predictor.MyHmmPredictor(
                filename=os.path.join(
                    os.path.dirname(__file__), 'modelsFinal/mp.xml'))
        mphmm.set_decoder('SSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSGLLLLLLLLLLLLLLLLLLLLCCCCCHHHHHHHHHHHHHHHHHHHHHHHHH')
        predicted = yield tornado.gen.Task(self.async_predict, 
                myhmm, query_data, True)
        predicted_sp = yield tornado.gen.Task(self.async_predict,
                sphmm, query_data, False)
        predicted_mp = yield tornado.gen.Task(self.async_predict,
                mphmm, query_data, False)
        
        predicted = self.convert_numpy_types(predicted, predicted_sp, predicted_mp)
        self.write(json.dumps(predicted))

    def async_predict(self, myhmm, dataset, reverse=True, callback=None):
        """Async wrapper for predict.
        Though usually myhmm.predict() doesn't take much time, 
        make it asynchrounous would be better as for performance."""
        callback(myhmm.predict(dataset, reverse))

    def convert_numpy_types(self, predicted, predicted_sp, predicted_mp):
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
            converted['likelihood_sp'] = predicted_sp[seq_id]['likelihood'].item()
            converted['likelihood_mp'] = predicted_mp[seq_id]['likelihood'].item()
            new_result[seq_id] = converted
        return new_result
        

class ResultPageHandler(tornado.web.RequestHandler):
    """ResultPageHandler"""

    def get(self, result_id):
        """show the result page, which is stored in DB."""
        query_data = self.application.db[result_id]
        self.render('result.html', 
                    query_id=result_id, 
                    query_data=query_data,
                    page_title="TA Protein Predictor : prediction result")

class Application(tornado.web.Application):
    """Web app"""
    def __init__(self):
        handlers = [(r'/', TopPageHandler),
                    (r'/predict', QueryHandler),
                    (r'/predict/([\w\-]+)', QueryAPIHandler),
                    (r'/result/([\w\-]+)', ResultPageHandler)]
        self.db = shelve.open(os.path.join(
            os.path.dirname(__file__), 'queries/db'))
        current_file_path = os.path.dirname(__file__)
        template_path = os.path.join(current_file_path, 'templates')
        static_path = os.path.join(current_file_path, 'static')
        tornado.web.Application.__init__(self, 
                handlers, 
                template_path=template_path,
                static_path=static_path,
                debug=True)

    def __del__(self):
        if self.db is not None:
            self.db.close()

if __name__ == '__main__':
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
