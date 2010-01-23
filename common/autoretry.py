###
### Copyright 2009 The Chicago Independent Radio Project
### All Rights Reserved.
###
### Licensed under the Apache License, Version 2.0 (the "License");
### you may not use this file except in compliance with the License.
### You may obtain a copy of the License at
###
###     http://www.apache.org/licenses/LICENSE-2.0
###
### Unless required by applicable law or agreed to in writing, software
### distributed under the License is distributed on an "AS IS" BASIS,
### WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
### See the License for the specific language governing permissions and
### limitations under the License.
###

import time
import logging
from google.appengine.runtime import apiproxy_errors
from google.appengine.datastore import datastore_pb

ERRORS = {datastore_pb.Error.TIMEOUT:'Timeout',
          datastore_pb.Error.CONCURRENT_TRANSACTION:'TransactionFailedError'}
                

class AutoRetry(object):
    """Autoretry is a workaround for GAE datastore timeout issues.  See http://code.google.com/p/chirpradio/issues/detail?id=78 or search the GAE group discussion list for "datastore timeout" for more information."""
    
    def __init__(self, obj):
        self.__obj = obj

    def __getattr__(self, attr):
        method = getattr(self.__obj, attr)
        def dispatcher(*args, **kw):
            return self.__run_in_retry_loop(method, args, kw)
        return dispatcher
    
    def __run_in_retry_loop(self, method, args, kw, attempts=5.0, interval=0.1, exponent=2.0):
        count = 0.0
        while 1:
            try:
                return method(*args, **kw)
            except apiproxy_errors.ApplicationError, e:

                errno = e.application_error
                if errno not in ERRORS: 
                    raise

                sleep = (exponent ** count) * interval
                count += 1.0
                if count > attempts: 
                    raise

                msg = "Datastore %s: retry #%d in %s seconds.\n%s"
                vals = ''
                if count == 1.0:
                    vals = '\n'.join([str(a) for a in args])
                logging.warning(msg % (ERRORS[errno], count, sleep, vals))

                time.sleep(sleep)

