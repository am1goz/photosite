import json

import psycopg2
from psycopg2._json import Json
from psycopg2 import extras, extensions
# from .better_json import BetterJSONEncoder
from better_json import BetterJSONEncoder


class Row(dict):
    """A dict that allows for object-like property access syntax."""

    def getattr(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def setattr(self, name, value):
        self[name] = value


class PostgresqlDatabaseError(Exception):
    pass


class BetterJson(Json):
    def dumps(self, obj):
        return json.dumps(obj, cls=BetterJSONEncoder)


class PgConnection(object):
    '''
    Sync wrapper for psycopg2
    '''

    cursor = None

    @staticmethod
    def iter_wrapper(cursor, arraysize=1000):
        """
        An iterator that uses fetchmany to keep memory usage down
        """
        while True:
            results = cursor.fetchmany(arraysize)
            if not results:
                break
            for result in results:
                yield result

    def __init__(self, database, **kwargs):
        kwargs['database'] = database
        kwargs['host'] = kwargs.get('host', 'localhost')
        kwargs['port'] = kwargs.get('port', 5432)

        self.connection = psycopg2.connect(**kwargs)
        extensions.register_type(extensions.UNICODE, self.connection)
        extensions.register_type(extensions.UNICODEARRAY, self.connection)
        extras.register_uuid(conn_or_curs=self.connection)
        # psycopg2.extras.register_json(conn_or_curs=self.connection, name='jsonb')
        extensions.register_adapter(dict, BetterJson)
        self.connection.autocommit = True

        self.cursor = self.connection.cursor()

    @staticmethod
    def result_wrapper(cursor):
        desc = cursor.description
        return [Row(zip([col[0] for col in desc], row))
                for row in cursor.fetchall()]

    def close(self):
        self.cursor.close()

    def execute(self, query, *parameters, **kwparameters):
        self.cursor.execute(query, kwparameters or parameters)

    def query(self, query, *parameters, **kwparameters):
        self.execute(query, *parameters, **kwparameters)

        return self.result_wrapper(self.cursor)

    def get(self, query, *parameters, **kwparameters):
        result = self.query(query, *parameters, **kwparameters)

        return result[0] if result else None

    def exists(self, query, *parameters, **kwparameters):
        result = self.query(query, *parameters, **kwparameters)
        return bool(result)

    def insert(self, query, *parameters, **kwparameters):
        q = '%s RETURNING id' % query
        result = self.query(q, *parameters, **kwparameters)
        return result[0]

    def update(self, query, *parameters, **kwparameters):
        self.execute(query, *parameters, **kwparameters)

    def delete(self, query, *parameters, **kwparameters):
        self.execute(query, *parameters, **kwparameters)

    # def get_or_create(self, table_name, val, ret_field='id', search_field='name', map_field=None, map_value={}):
    #     if not val:
    #         return None
    #     query = 'select %s from %s where %s = %%s' % (ret_field, table_name, search_field)
    #     result = self.get(query, val)
    #     if not result:
    #         fields = [search_field]
    #         values = [val]
    #         if map_field and map_field:
    #             fields.append(map_field)
    #             values.append(map_value.get(val, None))
    #         query = 'insert into %s (%s) values (%s) returning %s' % (table_name, ', '.join(fields), ', '.join(['%s']*len(values)), ret_field)
    #         result = self.query(query, *values)
    #     return result.get(ret_field, None) if result else None
