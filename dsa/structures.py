"""Linked list and binary tree helpers, matching LeetCode's node classes."""


class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


def to_linked(vals):
    dummy = tail = ListNode()
    for v in vals:
        tail.next = tail = ListNode(v)
    return dummy.next


def from_linked(head):
    vals = []
    while head:
        vals.append(head.val)
        head = head.next
    return vals


def to_tree(vals):
    """LeetCode level-order list, e.g. [3, 9, 20, None, None, 15, 7]."""
    if not vals or vals[0] is None:
        return None
    root = TreeNode(vals[0])
    queue, i = [root], 1
    for node in queue:
        for side in ('left', 'right'):
            if i < len(vals) and vals[i] is not None:
                child = TreeNode(vals[i])
                setattr(node, side, child)
                queue.append(child)
            i += 1
    return root


def from_tree(root):
    vals, queue = [], [root]
    for node in queue:
        vals.append(node.val if node else None)
        if node:
            queue += [node.left, node.right]
    while vals and vals[-1] is None:
        vals.pop()
    return vals
