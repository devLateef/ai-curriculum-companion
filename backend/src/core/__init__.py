"""Transport-agnostic pipeline: extraction, retrieval, verdicts.

Nothing here may import Flask, read a request object, or write to a response
stream. That constraint is what lets the evaluation harness and any future
batch pre-processing pass drive the same code the HTTP layer drives.
"""
