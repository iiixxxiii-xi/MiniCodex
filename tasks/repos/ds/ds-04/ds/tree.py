"""Binary tree helpers."""


class TreeNode:
    """A binary tree node."""

    def __init__(self, value, left=None, right=None):
        self.value = value
        self.left = left
        self.right = right


def height(node):
    """Return the height of the tree rooted at ``node``.

    The height is the number of nodes on the longest path from the root down
    to a leaf: an empty tree has height 0 and a single node has height 1.
    """
    if node is None:
        return 0
    if node.left is None and node.right is None:
        return 1
    return 1 + max(height(node.left), height(node.right))
