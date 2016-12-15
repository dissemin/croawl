
"""
This module implements a simple stream shuffling algorithm.
"""

def stream_shuffle(stream, batch_size=10000, key=(lambda x:x)):
    """
    :param stream: a generator of items
    :param batch_size: the number of items to fetch from the generator
        before ordering them by (hashed) key.
    """
    def sorting_key(elem):
        return key(elem).__hash__() % (32*batch_size)
    cur_batch = []
    old_batch = []
    for item in stream:
        # emit elements
        if old_batch:
            yield old_batch.pop()

        # accumulate elements
        if len(cur_batch) < batch_size:
            cur_batch.append(item)

        if len(cur_batch) == batch_size:
            # first shuffle them
            cur_batch.sort(key=sorting_key)
            # move them to the emitting batch
            old_batch = cur_batch
            cur_batch = []


    # if elements remain at the end, yield them
    batch = cur_batch + old_batch
    batch.sort(key=sorting_key)
    for elem in batch:
        yield elem


