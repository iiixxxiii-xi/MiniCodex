import pytest

from ds.ring import RingBuffer
from ds.stack import Stack


def test_stack_push_pop():
    s = Stack()
    s.push(1)
    s.push(2)
    assert s.pop() == 2
    assert s.pop() == 1


def test_stack_pop_empty_raises():
    s = Stack()
    with pytest.raises(IndexError):
        s.pop()


def test_stack_peek():
    s = Stack()
    s.push(10)
    s.push(20)
    assert s.peek() == 20


def test_stack_peek_empty_raises():
    s = Stack()
    with pytest.raises(IndexError):
        s.peek()


def test_stack_is_empty():
    s = Stack()
    assert s.is_empty()
    s.push(1)
    assert not s.is_empty()


def test_stack_len():
    s = Stack()
    assert len(s) == 0
    s.push(1)
    s.push(2)
    s.push(3)
    assert len(s) == 3


def test_stack_len_after_pop():
    s = Stack()
    s.push(1)
    s.push(2)
    s.pop()
    assert len(s) == 1


def test_ring_push_pop():
    r = RingBuffer(3)
    r.push(1)
    r.push(2)
    r.push(3)
    assert r.pop() == 1
    assert r.pop() == 2
    assert r.pop() == 3


def test_ring_full():
    r = RingBuffer(2)
    r.push(1)
    r.push(2)
    assert r.is_full()


def test_ring_push_full_raises():
    r = RingBuffer(1)
    r.push(1)
    with pytest.raises(OverflowError):
        r.push(2)


def test_ring_wraparound():
    r = RingBuffer(3)
    r.push(1)
    r.push(2)
    r.push(3)
    assert r.pop() == 1
    r.push(4)
    assert r.to_list() == [2, 3, 4]


def test_ring_wraparound_order():
    r = RingBuffer(2)
    r.push(1)
    r.push(2)
    r.pop()
    r.push(3)
    assert r.to_list() == [2, 3]


def test_ring_pop_empty_raises():
    r = RingBuffer(2)
    with pytest.raises(IndexError):
        r.pop()


def test_ring_peek():
    r = RingBuffer(2)
    r.push(5)
    r.push(6)
    assert r.peek() == 5


def test_ring_len():
    r = RingBuffer(3)
    assert len(r) == 0
    r.push(1)
    r.push(2)
    assert len(r) == 2
