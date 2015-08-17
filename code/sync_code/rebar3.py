# reusable barrier non-solution
count = 0
mutex = Semaphore(1)
turnstile1 = Semaphore(0)
turnstile2 = Semaphore(1)


## Thread code
# rendezvous

mutex.wait()
    count += 1
    if count == num_threads(): turnstile2.wait()
    if count == num_threads(): turnstile1.signal()
mutex.signal()

turnstile1.wait()
turnstile1.signal()

# critical point

mutex.wait()
    count -= 1
    if count == 0: turnstile1.wait()
    if count == 0: turnstile2.signal()
mutex.signal()

turnstile2.wait()
turnstile2.signal()
