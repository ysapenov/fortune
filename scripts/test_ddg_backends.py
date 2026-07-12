from duckduckgo_search import DDGS
import json

queries = [
    "Microsoft software engineer careers",
    "site:glassdoor.com/job-listing Microsoft software engineer",
    "site:lever.co OR site:greenhouse.io Microsoft software engineer",
    "intitle:\"software engineer\" Microsoft job"
]

backends = ["api", "html", "lite"]

def test():
    for query in queries:
        print(f"--- Testing query: {query} ---")
        for backend in backends:
            print(f"Backend: {backend}")
            try:
                with DDGS() as ddgs:
                    results = ddgs.text(query, max_results=3, backend=backend)
                    if results:
                        for r in results:
                            print(f"  - {r.get('title')}")
                            print(f"    {r.get('href')}")
                    else:
                        print("  (No results)")
            except Exception as e:
                print(f"  Error: {e}")

if __name__ == "__main__":
    test()
