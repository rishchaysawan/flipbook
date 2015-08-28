import webapp2
import jinja2
import os
from google.appengine.ext import db 

template_dir=os.path.join(os.path.dirname(__file__),'templates')
jinja_env=jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),autoescape=True)

class Customer(db.Model):
	email=db.StringProperty(required=True)
	name=db.StringProperty()
	password=db.StringProperty()

class Handler(webapp2.RequestHandler):
    def write(self,*a,**kw):
        self.response.write(*a,**kw)
    def render_str(self,template,**params):
        t=jinja_env.get_template(template)
        return t.render(params)
    def render(self,template,**kw):
        self.write(self.render_str(template,**kw))

class MainHandler(Handler):
    def get(self):
        self.render("index.html")


app = webapp2.WSGIApplication([
    ('/', MainHandler)
], debug=True)
