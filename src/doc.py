#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""© Ihor Mirzov, 2019-2021
Distributed under GNU General Public License v3.0

A tool to prepare new release of CrunchiX HTML help pages.
Extract official documentation into /doc/ folder, 
then run prepare_documentation() method.
"""

# Standard modules
import os
import re

# My modules
import path
import model
import tests

# Open 'ccx.html',
# find link to keyword help page
# and regenerate its HTML file
def save_html(doc_root, keyword_name, url):
    href = os.path.join(doc_root, 'ccx.html')
    if os.path.isfile(href):
        with open(href, 'r') as f:
            for line in f.readlines():
                match = re.search('node\d{3}\.html.{3}' + keyword_name, line) # regex to match href
                if match:
                    href = match.group(0)[:12]
                    break

        # Read html of the keyword page
        html = '<html><head><link rel="stylesheet" type="text/css" href="style.css"/></head><body>'
        with open(os.path.join(doc_root, href), 'r') as f:
            append = False
            cut_breakline = True
            for line in f.readlines():
                if '<!--End of Navigation Panel-->' in line:
                    append = True
                    continue
                if '<HR>' in  line:
                    break
                if '<PRE>' in line:
                    cut_breakline = False
                if '</PRE>' in line:
                    cut_breakline = True
                if append:
                    if cut_breakline:
                        line = line[:-1] + ' ' # replace '\n' with space
                    html += line
        html += '</body></html>'
        html = re.sub('<A.+?\">', '', html) # '?' makes it not greedy
        html = html.replace('</A>', '')
        with open(url, 'w') as f:
            f.write(html)

# Regenerate all HTML help pages
# Avoid spaces in html page names
def regenerate_documentation(KOM):
    for item in KOM.keywords:
        keyword_name = item.name[1:] # cut star
        html_page_name = re.sub(r'[ -]', '_', keyword_name)
        url = os.path.join(path.p.doc, html_page_name + '.html')
        save_html(path.p.doc, keyword_name, url)
        print(keyword_name, url)

# Deletes unneeded html files
def remove_html_trash(KOM):
    rm_list = ('ccx', 'footnode', 'index', 'node')
    for file_name in os.listdir(path.p.doc):
        if file_name.startswith(rm_list) \
            and file_name.endswith('.html'):
            file_name = os.path.join(path.p.doc, file_name)
            print(file_name)
            os.remove(file_name)

# Deletes unneeded images
def remove_png_trash():

    # Read contents of all HTML files in doc directory
    lines = []
    for file_name in os.listdir(path.p.doc):
        if file_name.endswith('.html'):
            file_name = os.path.join(path.p.doc, file_name)
            with open(file_name, 'r') as f:
                lines.extend(f.readlines())
    images = []
    regex = r'img\d+\.png'
    for line in lines:
        while True:
            match = re.search(regex, line)
            if match is not None:
                img = match.group(0)
                images.append(img)
                line = line[match.end():]
            else:
                break
    images = set(images)
    print(len(images), 'images')

    for file_name in os.listdir(path.p.doc):
        if file_name.endswith('.png'):
            if not file_name in images:
                file_name = os.path.join(path.p.doc, file_name)
                # print(file_name)
                os.remove(file_name)

# Regenerate all html files and remove trash
def prepare_documentation():
    KOM = model.kom.KOM()
    regenerate_documentation(KOM)
    remove_html_trash(KOM)
    remove_png_trash()

# Checks if HTML pages are generated for all keywords
@tests.test_wrapper()
def test():
    KOM = model.kom.KOM()

    keywords = [re.sub(r'[ -]', '_', kw.name[1:]) for kw in KOM.keywords]
    keywords = sorted(set(keywords))
    # print(keywords)
    print('Total {} keywords'.format(len(keywords)))
    pages = [fn for fn in os.listdir(path.p.doc) if fn.endswith('.html')]
    pages = sorted(pages)
    print('Total {} HTML pages'.format(len(pages)))
    # print(pages)
    if len(keywords) > len(pages):
        for page in pages:
            if page[:-5] in keywords:
                keywords.remove(page[:-5])
        print('Those keywords have no HTML pages:')
        print(keywords)

# Run test
if __name__ == '__main__':
    test()
    # prepare_documentation()
