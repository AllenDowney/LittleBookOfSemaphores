# reusable barrier non-solution
count = 0
mutex = Semaphore(1)
turnstile1 = Semaphore(0)
turnstile2 = Semaphore(1)


## Thread code
# rendezvous

mutex.wait()
    count += 1
    n = num_threads()
    if count == n: turnstile2.wait()
    if count == n: turnstile1.signal(n+1)
mutex.signal()

turnstile1.wait()

# critical point

mutex.wait()
    count -= 1
    n = num_threads()
    if count == 0: turnstile1.wait()
    if count == 0: turnstile2.signal(n+1)
mutex.signal()

turnstile2.wait()
