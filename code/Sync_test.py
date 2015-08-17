"""This module is part of Swampy, a suite of programs available from
allendowney.com/swampy.

Copyright 2011 Allen B. Downey
Distributed under the GNU General Public License at gnu.org/licenses/gpl.html.
"""

import unittest

import Sync

class Tests(unittest.TestCase):

    def test_sync_mutex(self):
        sync = Sync.Sync(['mutex.py'])

        threads = sync.get_threads()
        threadA = threads[0]
        column = threadA.column

        source = threadA.step()
        self.assertEqual(source, 'mutex.wait()')

        threadB = Sync.Thread(column)
        source = threadB.step()
        self.assertEqual(source, 'mutex.wait()')

        self.assertFalse(threadA.queued)
        self.assertTrue(threadB.queued)

        source = threadB.step()
        self.assertEqual(source, None)

        source = threadA.step()
        source = threadA.step()
        source = threadA.step()
        self.assertEqual(source, 'mutex.signal()')
        
        self.assertFalse(threadA.queued)
        self.assertFalse(threadB.queued)

        source = threadA.exec_line('pid = pid()', sync)
        self.assertEqual(sync.locals['pid'], 'A')

    def test_sync_conditional(self):
        sync = Sync.Sync(['sync_code/conditional.py'])
        threads = sync.get_threads()
        threadA = threads[0]

        source = threadA.step()
        self.assertEqual(source, 'if counter == 0:')

        source = threadA.step()
        self.assertEqual(source, '    print(True)')

        source = threadA.step()
        self.assertEqual(source, 'if counter == 1:')

        source = threadA.step()
        self.assertEqual(source, 'pass')

        source = threadA.step()
        source = threadA.step()
        self.assertEqual(source, 'else:')

        source = threadA.step()
        self.assertEqual(source, '    print(False)')

        source = threadA.step()
        source = threadA.step()
        self.assertEqual(source, '    print(True)')

        source = threadA.step()
        source = threadA.step()
        self.assertEqual(source, 'pass')


    def test_sync_while(self):
        sync = Sync.Sync(['sync_code/while.py'])
        threads = sync.get_threads()
        threadA = threads[0]

        source = threadA.step()
        self.assertEqual(source, 'while counter == 1:')

        source = threadA.step()
        self.assertEqual(source, 'while counter < 1:')

        source = threadA.step()
        self.assertEqual(source, '    counter += 1')

        source = threadA.step()
        self.assertEqual(source, 'while counter < 1:')

        source = threadA.step()
        self.assertEqual(source, 'pass')


if __name__ == '__main__':
    unittest.main()
