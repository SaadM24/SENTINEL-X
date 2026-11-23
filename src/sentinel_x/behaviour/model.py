"""Smoothed token and transition models. A list represents one ordered trace."""
from collections import Counter
import math

START, END, UNKNOWN = -1, -2, -3


class TraceModel:
    def __init__(self, alpha=0.5):
        if alpha <= 0:
            raise ValueError("alpha must be positive")
        self.alpha = alpha
        self.tokens = Counter()
        self.edges = Counter()
        self.sources = Counter()
        self.alphabet = set()

    def fit(self, traces):
        self.tokens.clear()
        self.edges.clear()
        self.sources.clear()
        for trace in traces:
            if not trace or any(token < 0 for token in trace):
                raise ValueError("expected a nonempty trace of nonnegative syscall IDs")
            previous = START
            for token in (*trace, END):
                self.tokens[token] += 1
                self.edges[previous, token] += 1
                self.sources[previous] += 1
                previous = token
        if not self.tokens:
            raise ValueError("no training traces")
        self.alphabet = set(self.tokens) | {UNKNOWN}
        self.smoothing_mass = len(self.alphabet) * self.alpha
        total = self.tokens.total() + self.smoothing_mass
        self.token_loss = {token: -math.log((self.tokens[token] + self.alpha) / total)
                           for token in self.alphabet}
        self.edge_loss = {edge: -math.log(self.probability(*edge)) for edge in self.edges}
        self.missing_loss = {s: -math.log(self.probability(s, UNKNOWN))
                             for s in self.alphabet | {START}}
        return self

    def probability(self, previous, token):
        return ((self.edges[previous, token] + self.alpha) /
                (self.sources[previous] + self.smoothing_mass))

    def score(self, trace):
        if not trace:
            raise ValueError("empty trace")
        unigram = markov = 0.0
        previous = START
        worst_loss, worst_index, worst_edge = -1.0, 0, ()
        for i, raw in enumerate((*trace, END)):
            token = raw if raw in self.alphabet else UNKNOWN
            unigram += self.token_loss[token]
            edge = previous, token
            loss = self.edge_loss.get(edge, self.missing_loss[previous])
            markov += loss
            if loss > worst_loss:
                worst_loss, worst_index, worst_edge = loss, i, edge
            previous = token
        size = len(trace) + 1
        return unigram / size, markov / size, worst_index, worst_edge
