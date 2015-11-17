PENDING = 'pending'
RESOLVED = 'resolved'
REJECTED = 'rejected'

class PromiseException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

def empty(resolve, reject):
    pass

def identity(value):
    return value

def thrower(reason):
    raise PromiseException(reason)

def resolve(promise, result):
    promise.state = RESOLVED
    promise.result = result
    if promise.complete is not None:
        promise.complete()
    execute(promise, result)

def reject(promise, reason):
    promise.state = REJECTED
    promise.result = reason
    if promise.complete is not None:
        promise.complete()
    execute(promise, reason)

def execute(promise, result):
    if not len(promise.jobs):
        return
    for job in promise.jobs:
        execute_job(promise, job, result)

def execute_job(promise, job, result):
    value = None
    try:
        value = job['resolve'](result) if promise.state == RESOLVED else job['reject'](result)
    except PromiseException as e:
        reject(job['promise'], e.value)
        return
    except Exception as e:
        reject(job['promise'], e)
        return

    if value is None:
        return

    if not value.__class__.__name__ == 'Promise':
        resolve(job['promise'], value)
        return

    if job['promise'].state != PENDING:
        resolve(job['promise'], value.result)
        return

    def on_complete():
        if value.state == RESOLVED:
            resolve(job['promise'], value.result)
        else:
            reject(job['promise'], value.result)

    if value.state != PENDING:
        on_complete()
        return

    value.complete = on_complete

class Promise:
    def __init__(self, fn):
        self.state = PENDING
        self.result = None
        self.jobs = []
        self.complete = None

        promise = self

        try:
            fn(lambda result: resolve(promise, result), lambda reason: reject(promise, reason))
        except Exception as e:
            reject(promise, e)

    @staticmethod
    def resolve(result):
        promise = Promise(empty)
        resolve(promise, result)
        return promise
    
    @staticmethod
    def reject(reason):
        promise = Promise(empty)
        reject(promise, reason)
        return promise

    def then(self, on_resolve, on_reject):
        job = {
            'promise': Promise(empty),
            'resolve': on_resolve if on_resolve is not None else identity,
            'reject': on_reject if on_reject is not None else thrower
        }
        if self.state == PENDING:
            self.jobs.append(job)
        else:
            execute_job(self, job, self.result)
        return job['promise']

    def catch(self, on_reject):
        return self.then(None, on_reject)
