# Directory structure

```
education/
 |- content/ (contains the markdown formatted content for each non-external tutorial)
 |- thumbnails/ (optionally contains png images to be displayed on each card)
 |- index.json (contains title/description/link/etc. for each card)
```

# Content Formatting

Tutorial pages are created with Markdown syntax similar to [standard markdown](https://www.markdownguide.org/basic-syntax/) or [github-flavored markdown](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax) with a few notable extensions explained below. Pages should be saved as `[page-slug]`.md in the `content/` directory.

## Extensions

### Admonitions or Callouts

These are "info-boxes" used for displaying important side content. There are 3 types: `prereqs`, `info`, and `warning`.
To use them, start a block with `!!!` followed by the type and a title enclosed in double quotes. The content of the block follows on the next line, indented by 4 spaces.

#### Prereqs

The prereqs callout is optional but should be placed at the very top of the tutorial and outlines what a user needs before following a tutorial (system requirements, knowledge, etc.). The content does not necessarily need to be an ordered or unordered list, it can be a simple paragraph as well.

Example:
```
!!! prereqs "Prerequisites"
    1. Have [Docker](https://www.docker.com/) installed on your computer
    2. Be familiar with `bash` or the linux shell
```
![Screenshot from 2022-11-14 13-28-52](https://user-images.githubusercontent.com/46429375/201759444-0162d5ee-7552-4c34-b117-f1f03e5928c1.png)

#### Info and Warning

The info and warning callouts can be used anywhere on the page and are meant to display important information in a highlighted block.

Examples:
```
!!! warning "DANGER"
    The `rm` command will permanently delete a file from your system. Use with caution.
```
![Screenshot from 2022-11-14 13-37-21](https://user-images.githubusercontent.com/46429375/201760872-a74410ba-9ef5-4a72-b1eb-22c8231d20d7.png)

```
!!! info "Note"
    More information on the FAIR principles can be found [here](https://www.go-fair.org/fair-principles/)
```
![Screenshot from 2022-11-14 13-37-32](https://user-images.githubusercontent.com/46429375/201760997-0678207f-b386-4990-8eaa-1667d7ed318b.png)

### Video Embedding

Similar to how you can embed an image in markdown with `![alt text](link)`, you are able to embed videos uploaded to Youtube or Vimeo with the same syntax. The regular video link (`https://www.youtube.com/watch?...` or `https://vimeo.com/...`) should be used instead of the embed link.

Example:
```
![Keyboard Cat Video](https://www.youtube.com/watch?v=J---aiyznGQ)
```
![Screenshot from 2022-11-14 13-50-04](https://user-images.githubusercontent.com/46429375/201762834-c2a30b76-c8cd-4613-b21b-c7163b4dda8c.png)

### Table of Contents

To insert a table of contents into the page use `[TOC]`. This is completely optional, however should be placed below the prereqs callout or at the top of the page if it does not exist. The table of contents indexes the sections in the page and produces anchor links to the headings. It is given the style `float: right`, meaning it will appear on the right of the page and the rest of the contents will wrap around it.

Example:
```
!!! prereqs "Prerequisites"
    1. Have [Docker](https://www.docker.com/) installed on your computer
    2. Be familiar with `bash` or the linux shell

[TOC]

# Main Section

Lorem ipsum dolor sit amet...

## 1. First sub-section

Sed ut perspiciatis unde omnis...

### a. Point A

### b. Point B

## 2. Second sub-section

# Second Main Section
```
![Screenshot from 2022-11-14 14-02-33](https://user-images.githubusercontent.com/46429375/201764837-9f51b012-06f0-474f-9beb-107a108ae429.png)
