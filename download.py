from icrawler.builtin import GoogleImageCrawler

keywords = [
    "tomato leaf",
    "rice leaf",
    "banana leaf",
    "mango leaf",
    "cotton leaf",
    "mobile phone",
    "plastic bottle",
    "human hand",
    "diagram image",
    "flowchart diagram",
    "screenshot",
    "document page"
]

for word in keywords:
    crawler = GoogleImageCrawler(storage={'root_dir': 'dataset/NotSugarcane'})
    crawler.crawl(keyword=word, max_num=30)