from googlesearch import search

results = list(search("microsoft careers software engineer", num_results=5, advanced=True))
for r in results:
    print(r.title)
    print(r.url)
    print(r.description)
    print("---")
