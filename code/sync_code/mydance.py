# Dance problem from Exam 1
leaders = Semaphore(50) # NOTE: FIFTY LEADERS
followers = Semaphore(0)
leaders_done = Semaphore(0)
followers_done = Semaphore(0)

## Thread A
leaders.wait() # DOES NOT ALWAYS BLOCK
followers.signal() # wake up a follower, tell her she's mah gal
# dance()
# dance()
# dance()
leaders_done.signal()
followers_done.wait()


## Thread B
followers.wait() # wait for a leader to ask me to dance
# dance()
# dance()
# dance()
followers_done.signal()
leaders_done.wait()
leaders.signal()

