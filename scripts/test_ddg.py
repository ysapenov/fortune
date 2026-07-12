from duckduckgo_search import DDGS

with DDGS() as ddgs:
    results = [r for r in ddgs.text('site:greenhouse.io OR site:lever.co "Stripe" "Software Engineer"', max_results=3)]
    print(results)
