#!/usr/bin/env python
#
# Copyright (c) 2015 Pavel Lazar pavel.lazar (at) gmail.com
#
# The Software is provided WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.
#####################################################################

import tornado.web
import tornado.escape
import tornado.ioloop


class MessageHandler(tornado.web.RequestHandler):
    def post(self, message_type, **kwargs):
        print self.request.body


def main():
    app = tornado.web.Application([
        (r'/message/(.*)', MessageHandler)
    ])

    app.listen(3637)
    tornado.ioloop.IOLoop.current().start()

if __name__ == '__main__':
    main()