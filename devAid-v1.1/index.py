import hashlib
import os
import string
import uuid
from abc import ABC
import random
import time

import tornado
from tornado import web, ioloop

from postgresql import PgConnection


# Логин


class BaseHandler(tornado.web.RequestHandler, ABC):

    def get_current_user(self):
        return self.get_secure_cookie("login")

    @property
    def db(self):
        return self.application.db


# Рендер странички сайта


class PageHandler(BaseHandler, ABC):
    @tornado.web.authenticated
    def get(self):
        if not self.current_user:
            self.redirect(r'/login')
        self.render("pages/index.html")


class LoginHandler(BaseHandler, ABC):

    def get(self):
        self.render("pages/login.html")

    def post(self):
        current_log = self.get_argument("login")
        current_pwd = hashlib.md5(self.get_argument("password").encode("utf-8"))
        self.set_secure_cookie("login", current_log)

        if not self.db.exists('select * '
                              'from register '
                              'where login = %s AND pwd = %s', current_log, current_pwd.hexdigest()):
            log_error = 'Такого пользователя не существует'
            self.render("pages/login-error.html")
        else:
            self.redirect(r'/index')


class RegisterHandler(BaseHandler, ABC):

    def get(self):
        self.render("pages/register.html")

    def post(self):
        hash_pwd = hashlib.md5(self.get_argument("pwd").encode("utf-8"))
        current_login = self.get_argument("login")

        login_check = self.db.exists('select * from register where login = %s', current_login)
        email_check = self.db.exists('select * from register where email = %s', (self.get_argument("email")))

        print(self.get_argument("login"), self.get_argument("email"), self.get_argument("pwd"))
        if not login_check:
            if not email_check:
                self.db.insert('insert into register (login,pwd,email) values (%s,%s,%s)',
                               current_login,
                               hash_pwd.hexdigest(),
                               self.get_argument("email")
                               )
            else:
                self.render("pages/register-email-error.html")
        else:
            self.render("pages/register-login-error.html")
        self.redirect(r'/index')


class ImageUploadHandler(BaseHandler, ABC):
    def get(self):
        self.render("pages/image-download.html")

    def post(self):
        a_file = self.request.files['image'][0]
        extension = os.path.splitext(a_file.filename)[1]

        file_name = str(uuid.uuid4())
        output_file = open(os.path.abspath(os.path.dirname("img/")) + '/' + file_name + extension, 'wb')
        output_file.write(a_file.body)
        self.write( a_file.filename + " has been uploaded.")
        time.sleep(3)
        self.redirect(r'/index')


class IndexHandler(BaseHandler, ABC):
    def get(self):
        self.render("pages/index.html")

    def post(self):
        self.set_secure_cookie("login", " ", expires_days=0)
        self.redirect(r'/')


class Apps(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/login', LoginHandler),
            (r'/', PageHandler),
            (r'/img', ImageUploadHandler),
            (r'/register', RegisterHandler),
            (r'/index', IndexHandler)
        ]

        settings = dict(
            cookie_secret='61oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=',
            login_url=r'/login',
            static_path=os.path.abspath(os.path.dirname("css")),

        )

        web.Application.__init__(self, handlers, **settings)
        self._db = PgConnection('photosite',
                                user='photosite',
                                password='photosite',
                                host='localhost',
                                port=5432,
                                )

    @property
    def db(self):
        return self._db


if __name__ == "__main__":
    app = Apps()
    http_server = tornado.httpserver.HTTPServer(app, xheaders=True)

    http_server.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
