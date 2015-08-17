
def pairiter(seq):
    it = iter(seq)
    while True:
        yield [it.next(), it.next()]

def pair(seq):
    return [x for x in pairiter(t)]

t = range(10)
y = [x for x in pair(t)]
print(y)

print(pair(t))
