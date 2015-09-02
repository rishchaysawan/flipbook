import webapp2
import jinja2
import os
import hashlib
import random
import string
from google.appengine.ext import db 

template_dir=os.path.join(os.path.dirname(__file__),'templates')
jinja_env=jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),autoescape=True)

def make_salt():
    return "".join(random.choice(string.letters) for x in range (0,5))

def make_pw_hash(name,pw,salt=None):
    if not salt:
        salt=make_salt()
    h=hashlib.sha256(name+pw+salt).hexdigest()
    return "%s,%s"%(h,salt)


class Customer(db.Model):
	email=db.StringProperty(required=True)
	name=db.StringProperty(required=True)
	password=db.StringProperty(required=True)

class Products(db.Model):
    product_id=db.IntegerProperty(required=True)
    category=db.StringProperty(required=True)
    price=db.IntegerProperty(required=True)
    brand=db.StringProperty(required=True)
    quantity=db.IntegerProperty(required=True)
    info=db.StringProperty(required=True)
    image=db.BlobProperty()
    discount=db.IntegerProperty(required=True)

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

class LoginHandler(Handler):
    def get(self):
        self.render("login.html")

class LoginWithEmail(Handler):
    def get(self):
        self.render("LoginWithEmail.html")

class NewsHandler(Handler):
     def get(self):
        self.render("newsfeed.html")
        #mail=""
        #posts=db.GqlQuery("select * from share order by time")
        #friends=db.GqlQuery("select * from person where email=%s"%mail)
        #f=[]
        #p=[]

        #for friend in friends:
            #f.append(friend.friendemail)


        #for post in posts:
            #if post.email in f:
            #p.append([post]) 

    
        #cursor=db.GqlQuery("select * from share where email IN(select friendemail from person" +
        #                    "where email=mail) order by time")

        #if len(p):
           #self.render("newsfeed.html",news=p)

        #else:  
            #self.write("no sharing")
               



class SignupHandler(Handler):
    def write_form(self,errorConfirm="",name="",password="",confirm="",mail="",userExists=""):
        self.render("signup.html",errorConfirm=errorConfirm,name=name,password=password,confirm=confirm,mail=mail,userExists=userExists)
    def get(self):
        self.write_form()
    def post(self):
        username=self.request.get('username')
        password=self.request.get('password')
        confirm_password=self.request.get('confirm_password')
        mail=self.request.get('email')
        errorMail=""
        errorUser=""
        errorConfirm=""
        errorPassword=""
        if confirm_password!=password:
            errorConfirm="Password didn't match"
            confirm_password=""
            password=""
        if  errorConfirm:
            self.write_form(errorConfirm=errorConfirm,name=username,password=password,confirm=confirm_password,mail=mail)
        else:
            username=str(username)
            password=str(password)
            mail=str(mail)
            #cursor=Users.all().filter('Username=',username).get()
            cursor=db.GqlQuery("Select * from Customer  where email = '%s'"%mail)
            if cursor.get():
                password=""
                confirm_password=""
                self.write_form(errorConfirm,username,password,confirm_password,mail,"Please enter different email")
            else:
                h_password=make_pw_hash(username,password)
                obj=Customer(name=username,password=h_password,email=mail)
                obj.put()
                self.redirect("/newsfeed")
app = webapp2.WSGIApplication([
    ('/', MainHandler),('/login',LoginHandler),('/loginEmail',LoginWithEmail),
    ('/signup',SignupHandler),('/newsfeed',NewsHandler)
], debug=True)
