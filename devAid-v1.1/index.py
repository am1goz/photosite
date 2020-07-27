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
        login_ids = self.current_user.decode()

        login_id = self.db.query("SELECT id FROM register WHERE login = %s", login_ids)
        for key in login_id:
            for subkey in key:
                login_id = int(key[subkey])
        albums = self.db.query("SELECT * FROM albums WHERE user_id = %s", login_id)

        self.render("pages/index.html", albums=albums)

    def post(self):
        self.clear_cookie("login")
        self.redirect(r'/')


class LoginHandler(BaseHandler, ABC):

    def get(self):
        log_error = ""
        self.render("pages/login.html", log_error=log_error)

    def post(self):
        current_log = self.get_argument("login")
        current_pwd = hashlib.md5(self.get_argument("password").encode("utf-8"))
        self.set_secure_cookie("login", current_log)

        if not self.db.exists('select * '
                              'from register '
                              'where login = %s AND pwd = %s', current_log, current_pwd.hexdigest()):
            log_error = 'Такого пользователя не существует'
            self.render("pages/login.html", log_error=log_error)
            return
        else:
            self.redirect(r'/')


class RegisterHandler(BaseHandler, ABC):

    def get(self):
        log_error = ""
        email_error = ""
        self.render("pages/register.html", log_error=log_error, email_error=email_error)

    def post(self):
        hash_pwd = hashlib.md5(self.get_argument("pwd").encode("utf-8"))
        current_login = self.get_argument("login")

        login_check = self.db.exists('select * from register where login = %s', current_login)
        email_check = self.db.exists('select * from register where email = %s', (self.get_argument("email")))

        if not login_check:
            if not email_check:
                self.db.insert('insert into register (login,pwd,email) values (%s,%s,%s)',
                               current_login,
                               hash_pwd.hexdigest(),
                               self.get_argument("email")
                               )
            else:
                email_error = "Пользователь с такой почтой уже существует, попробуйте снова."
                self.render("pages/register.html", email_error=email_error)
                return
        else:
            log_error = "Пользователь с таким именем уже существует, попробуйте снова"
            email_error = ""
            self.render("pages/register.html", log_error=log_error, email_error=email_error)
            return
        self.redirect(r'/')


class AlbumUploadHandler(BaseHandler, ABC):
    def get(self, ids):
        albums = self.db.query("SELECT * FROM albums WHERE id=%s", ids)
        images = self.db.query("SELECT * FROM images WHERE album_id=%s", ids)
        self.render("pages/image-download.html", albums=albums, images=images)

    def post(self, ids):
        a_file = self.request.files['image'][0]
        extension = os.path.splitext(a_file.filename)[1]

        file_name = str(uuid.uuid4())
        output_file = open(os.path.abspath(os.path.dirname("img/")) + '/' + file_name + extension, 'wb')
        output_file.write(a_file.body)
        test = output_file.name.split('/devAid-v1.1')
        test = ".." + test[1]
        self.db.insert("INSERT INTO images (album_id, name, path) VALUES (%s,%s,%s)", ids, file_name + extension, test)
        self.redirect(r'/')


class AlbumCreateHandler(BaseHandler, ABC):

    def get(self):
        message = ""
        self.render("pages/album-create-form.html", message=message)

    def post(self):
        album_name = self.get_argument("name")
        album_description = self.get_argument("description")
        if not album_name or not album_description:
            message = "Одно из полей пустое, пожалуйста, заполните оба поля"
            self.render("pages/album-create-form.html", message=message)
            return

        user = self.current_user.decode()
        user = self.db.query("SELECT id FROM register WHERE login = %s", user)
        for key in user:
            for subkey in key:
                user_ids = int(key[subkey])

        self.db.insert("INSERT INTO albums (user_id, name, description) VALUES (%s,%s,%s)", user_ids,
                       album_name, album_description)
        self.redirect(r"/")


class AlbumEditHandler(BaseHandler, ABC):
    def get(self, ids):
        message = ""
        albums = self.db.query("SELECT * FROM albums WHERE id=%s", ids)
        self.render("pages/album-edit-form.html", albums=albums, message=message)

    def post(self, ids):
        message = ""
        if self.get_argument("name") or self.get_argument("description"):
            self.db.update("UPDATE albums SET name = %s, description = %s WHERE id = %s", self.get_argument("name"),
                       self.get_argument("description"), ids)
        else:
            message = "Одно из полей пустое, заполните, пожалуйста, оба поля."
            albums = self.db.query("SELECT * FROM albums WHERE id=%s", ids)
            self.render("pages/album-edit-form.html", message=message, albums=albums)
            return
        self.redirect(r'/')


class Apps(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/login', LoginHandler),
            (r'/', PageHandler),
            (r'/register', RegisterHandler),
            (r'/album', AlbumCreateHandler),
            (r'/album/(\d+)', AlbumUploadHandler),
            (r'/album-edit/(\d+)', AlbumEditHandler)
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
