# reusable barrier non-solution
count = 0
mutex = Semaphore(1)
turnstile = Semaphore(0)


## Thread code
# rendezvous

mutex.wait()
    count += 1
    if count == num_threads(): turnstile.signal()
mutex.signal()

turnstile.wait()
turnstile.signal()

# critical point

mutex.wait()
    count -= 1
    if count == 0: turnstile.wait()
mutex.signal()
