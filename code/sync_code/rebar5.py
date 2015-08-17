# reusable barrier non-solution
count = 0
mutex = Semaphore(1)
turnstile1 = Semaphore(0)
turnstile2 = Semaphore(0)


## Thread code
# rendezvous

n = num_threads()

mutex.wait()
    count += 1
    if count == n: turnstile1.signal(n)
mutex.signal()

turnstile1.wait()

# critical point

mutex.wait()
    count -= 1
    if count == 0: turnstile2.signal(n)
mutex.signal()

turnstile2.wait()
