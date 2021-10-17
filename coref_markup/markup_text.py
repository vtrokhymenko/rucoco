import bisect
from collections import defaultdict
import tkinter as tk
from typing import *

from coref_markup import utils
from coref_markup.markup import Span


class MarkupText(tk.Text):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configure(state="disabled")
        self.tag_configure("sel", underline=True)
        self.clear_tags()

    def add_highlight(self, span: Span, entity_idx: int, color: str):
        tag = f"e{span}"
        self.tag_add(tag, *span)
        self.tag_configure(tag, background=color)

        self.tag2entity[tag] = entity_idx
        self.entity2spans[entity_idx].append(span)

    def add_extra_highlight(self, span: Span, underline: bool = True):
        if span not in self.extra_highlights:
            tag = f"e{span}"
            color = self.tag_cget(tag, "background")
            self.extra_highlights[span] = color
            self.tag_configure(tag, background=utils.multiply_color(color, 1.2), underline=underline)

    def clear_selection(self):
        self.tag_remove("sel", "1.0", tk.END)

    def clear_tags(self):
        for tag in self.tag_names():
            self.tag_delete(tag)
        self.entity2spans: Dict[int, List[Span]] = defaultdict(list)
        self.tag2entity: Dict[str, int] = {}
        self.extra_highlights: Dict[Span, str] = {}  # span -> original color

    def convert_char_to_tk(self, span: Tuple[int, int]) -> Span:
        """ Converts char offset notation to tkinter internal notation. """
        return tuple(self.index(f"1.0+{i}c") for i in span)

    def convert_tk_to_char(self, tk_span: Span) -> Tuple[int, int]:
        """ Converts tkinter internal notation to tuple of ints. """
        return tuple(self.convert_to_int_index(i) for i in tk_span)

    def convert_to_int_index(self, index: str) -> int:
        """ Converts tkinter string index to int """
        if index == "1.0":
            return 0
        return self.count("1.0", index, "chars")[0]

    def get_entity_label(self, entity_idx: int) -> str:
        first_span = min(self.entity2spans[entity_idx], key=self.convert_tk_to_char)
        return self.get(*first_span)[:32]

    def get_selection_indices(self) -> Span:
        try:
            return self.index(tk.SEL_FIRST), self.index(tk.SEL_LAST)
        except tk.TclError:
            raise RuntimeError("error: no text selected")

    def get_spans_at_index(self, index: str) -> Iterable[Span]:
        for tag in self.tag_names(index):
            if tag.startswith("e"):
                yield self.index(f"{tag}.first"), self.index(f"{tag}.last")

    def fix_overlapping_highlights(self):
        # Longer spans first
        all_spans = sorted(((span, entity_idx) for entity_idx, spans in self.entity2spans.items() for span in spans),
                           key=lambda x: self.span_length(x[0]), reverse=True)
        for span, entity_idx in all_spans:
            tags = [tag for tag in self.tag_names(span[0]) if tag.startswith("e")]
            if len(tags) > 1:
                self_in_self = sum(1 for tag in tags if self.tag2entity[tag] == entity_idx) - 1
                tag = f"e{span}"
                self.tag_raise(tag)
                self.tag_configure(tag, background=utils.multiply_color(self.tag_cget(tag, "background"),
                                                                        1 - 0.15 * self_in_self))

    def remove_extra_highlight(self, span: Span):
        if span in self.extra_highlights:
            tag = f"e{span}"
            color = self.extra_highlights[span]

            # tk uses "" as the absense of value
            # if underline=False, then this will conflict with other tags underline=True
            self.tag_configure(tag, background=color, underline="")

            del self.extra_highlights[span]

    def selection_exists(self) -> bool:
        return len(self.tag_ranges("sel")) > 0

    def set_text(self, text: str):
        self.configure(state="normal")
        self.delete("1.0", tk.END)
        self.insert("end", text)
        self.configure(state="disabled")

    def span_length(self, span: Span) -> int:
        return self.count(*span, "chars")
