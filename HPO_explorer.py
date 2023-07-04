import pronto
from functools import lru_cache


class HPO_explorer:
    def __init__(self, ontology_file):
        self.ont = pronto.ontology.Ontology(ontology_file)
        self.preprocessed_terms = self._preprocess_terms()

    def _preprocess_terms(self):
        preprocessed_terms = []
        for term in self.ont.terms():
            full_desc = (
                str(term.name).lower()
                + " "
                + " ".join(syn.description.lower() for syn in term.synonyms)
                + " "
                + str(term.definition).lower()
            )
            preprocessed_terms.append((term.id, term.name, full_desc))
        return preprocessed_terms

    @lru_cache(maxsize=1024)
    def find_terms(self, input, limit=None) -> list:
        if input != str.strip(input):
            return self.find_terms(str.strip(input), limit=limit)

        if not input or len(input) < 3:
            return []

        primary = []
        secondary = []
        words = input.lower().split()
        for term_id, term_name, full_desc in self.preprocessed_terms:
            if limit and limit <= len(primary):
                return (primary + secondary)[:limit]

            term = self.ont[term_id]
            if term.obsolete:
                continue

            # Check if all words in input are in the term name
            if all(word in term_name.lower() for word in words):
                primary.append((term_id, term_name))
            # Check synonyms
            elif 0 < len(term.synonyms) and all(word in full_desc for word in words):
                # The first synonym or definition with the most words in common with the input

                l = []
                for syn in term.synonyms:
                    l.append(syn.description)
                l.append(str(term.definition))

                syn = max(
                    l,
                    key=lambda s: 0
                    if s == term_name
                    else sum(word in s.lower() for word in words),
                )
                secondary.append((term_id, term_name, syn))

        return (primary + secondary)[:limit]

    @lru_cache(maxsize=1024)
    def get_superterms(self, term_id: str, distance: int | None = None) -> list:
        if not term_id or term_id not in self.ont:
            return []

        term: pronto.term.Term = self.ont[term_id]
        superterms = []
        results = term.superclasses(distance=distance, with_self=False)
        for superterm in results:
            superterms.append((superterm.id, superterm.name))

        return superterms

    def create_json_file(self):
        import json

        with open("hp.json", "w") as f:
            # The JSON file should contain only HPO_ID, name, definition, and synonyms
            d = {}
            for term in self.ont.terms():
                d[term.id] = {
                    "name": term.name,
                    "definition": str(term.definition),
                    "synonyms": [syn.description for syn in term.synonyms],
                }
            json.dump(d, f, indent=2)

    def create_jsonl_file(self):
        with open("hp.jsonl", "w") as f:
            l = []
            t = list(self.ont.terms())[1:]  # Skip the root term
            for term in t:
                l.append(f'{{"prompt": "{term.name}", "completion": "{term.id}"}}')
                # l.append(
                #     f'{{"prompt": "{term.definition}", "completion": "{term.id}"}}'
                # )
                # for syn in term.synonyms:
                #     l.append(
                #         f'{{"prompt": "{syn.description}", "completion": "{term.id}"}}'
                #     )
            f.write("\n".join(l))


if __name__ == "__main__":
    hpo = HPO_explorer("hp.obo")

    hpo.create_json_file()
    hpo.create_jsonl_file()

    # Test the function with an example term
    print(hpo.find_terms("Weight", limit=15), "\n")

    # Find the superterms of the term 'Childhood-onset truncal obesity'
    print(hpo.get_superterms("HP:0008915", distance=3))
