# -*- coding: utf-8 -*-

from app.api.scheme import error_codes
import json, time


class Error(Exception):

    def __init__(self, err=None, **kwargs):
        if err is not None:
            self.errcode = err[0]
            self.errmsg = err[1]
            if kwargs:
                self.errmsg = self.errmsg.format(**kwargs)
            self.err = err
        else:
            self.err = error_codes.SERVER_ERROR
            self.errcode = error_codes.SERVER_ERROR[0]
            self.errmsg = error_codes.SERVER_ERROR[1]
        super(Error, self).__init__(self.errmsg, None)

    def __str__(self):
        return "错误码: {}, 错误内容: {}".format(self.errcode, self.errmsg)


class CustomMessageError(Error):

    def __init__(self, message):
        super().__init__(err=error_codes.CUSTOM_MESSAGE_ERROR, message=message)


class ErrorStream(Error):

    @staticmethod
    def error_event(error_message):
        """
        生成错误事件
        """
        data = {"event": "error", "answer": error_message, "createdAt": int(time.time())}
        return f'data: {json.dumps(data)}\n\n'

    @staticmethod
    def status_event(status: dict):
        """
        生成错误事件
        """
        data = {"event": "status", "createdAt": int(time.time())}
        data.update(status)
        return f'data: {json.dumps(data)}\n\n'