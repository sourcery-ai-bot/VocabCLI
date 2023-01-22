from collections import Counter
from heapq import nlargest
from string import punctuation
import nltk
import pandas as pd
import regex as re
import requests
import rich
import spacy
import textstat
import torch
import trafilatura
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table
from spacy.lang.en.stop_words import STOP_WORDS
from spacytextblob.spacytextblob import SpacyTextBlob
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from rich.panel import Panel
from rich.table import Table
from rich import print, box
from rich.columns import Columns
from typing import *

from rich.progress import Progress, SpinnerColumn, TextColumn
 

# TODO: @atharva - add proper response headers and browser details to prevent false IP blocks.


def check_url_or_text(value: str) -> bool:
    """
    Checks if the value is a URL or a text
    1. Try to get the response from the URL, if we get a response, then it is a URL
    2. If we get an exception, then it is a text

    Args:
        value (str): URL or text to be checked

    Returns:
        bool: True if the value is a URL, False if the value is a text

    Raises:
        requests.exceptions.MissingSchema: If the URL is missing the schema
        requests.exceptions.InvalidSchema: If the URL has an invalid schema
        requests.exceptions.InvalidURL: If the URL is invalid
    """

    try:
        response = requests.get(value)
    except requests.exceptions.MissingSchema:
        return False
    except requests.exceptions.InvalidSchema:
        return False
    except requests.exceptions.InvalidURL:
        return False
    return True



def parse_text_from_web(webURL: str) -> str:
    """
    Extracts the text from the main content of the web page. Removes the ads, comments, navigation bar, footer, html tags, etc
    1. Download the web page using trafilatura
    2. Extract the text from the downloaded web page using trafilatura
    3. Return the extracted text

    Args:
        webURL (str): URL of the web page

    Returns:
        str: clean text from the web page

    Raises:
        trafilatura.errors.FetchingError: If the URL is invalid or the server is down
    """

    downloaded = trafilatura.fetch_url(webURL)
    return trafilatura.extract(downloaded, include_comments=False, include_tables=False, with_metadata=False, include_formatting=True, target_language='en', include_images= False)




def cleanup_text(text: str) -> str:
    """
    Clean up the text by removing special characters, numbers, whitespaces, etc for further processing and to improve the accuracy of the model.
    1. Remove the non-ascii characters
    2. Remove the numbers
    3. Remove the whitespaces
    4. Remove the special characters except full stop and apostrophe
    5. Convert the text to lowercase
    6. Remove the leading and trailing whitespaces
    7. Split the text into words without messing up the punctuation
    
    Args:
        text (str): text to be cleaned up

    Returns:
        str: cleaned up text
    """

    text = re.sub("\xc2\xa0", "", text)  # Deal with some weird tokens
    text = re.sub(r'\d+', '', text)  # remove numbers
    text = re.sub(r'\s+', ' ', text)  # remove whitespaces
    # remove special characters except full stop and apostrophe
    text = re.sub(r'[^a-zA-Z0-9\s.]', '', text)
    # text = text.lower()  # convert text to lowercase
    text = text.strip()  # remove leading and trailing whitespaces
    text = text.encode('ascii', 'ignore').decode(
        'ascii')  # remove non-ascii characters
    
    # split text into words without messing up the punctuation
    text = re.findall(r"[\w']+|[.,!?;]", text)
    
    return text
    
    

def censor_bad_words_strict(text: str) -> None:
    """
    Removes the bad words from the text and replaces them with asterisks completely and prints the censor text
    1. First we check if the text is a URL, if yes, then we parse the text from it and then use the model
    2. If the text is not a URL, then we directly use the model
    3. Remove the punctuations and convert text to lowercase
    4. Read the bad words from the file and store them in a list
    5. Split the text into words and for each word, we check if it is a bad word, if yes, then we replace it with asterisks
    6. Print the censored text and the number of bad words censored
    
    Args:
        text (str): text that needs to be censored
    """
    #----------------- Spinner -----------------#
    with Progress(
        SpinnerColumn(spinner_name="monkey", style="bold violet"),
        TextColumn("[progress.description]{task.description}", justify="left", style="bold cyan"),
        transient=True,
    ) as progress:
        progress.add_task(description="Censoring...", total=None)
    #----------------- Spinner -----------------#
    
    
        # check if the content is a URL, if yes, then parse the text from it and then use the model
        if isWebURL := check_url_or_text(text):
            print(Panel(title="[b reverse green]  Processing...  [/b reverse green]",
                        title_align="center",
                        padding=(1, 1),
                        renderable="URL detected 🌐")
                )
            text = parse_text_from_web(text)

        # if text and not URL, then directly use the model
        if not isWebURL:
            print(Panel(title="[b reverse yellow]  Warning!  [/b reverse yellow]",
                        title_align="center",
                        padding=(1, 1),
                        renderable="This is not a valid URL. Processing it as text... 📃")
                )
            
        text = cleanup_text(text)
        new_text = ''   
        offensive_words=0 

        with open('modules/_bad_words.txt', mode='r', encoding='utf-8') as f:
            bad_words = f.read().splitlines()
            bad_words_plural = [bad_words[i]+'s' for i in range(len(bad_words))]
            bad_words = bad_words + bad_words_plural
        
        for word in text:
            if word.lower() in bad_words:
                offensive_words+=1
                word = word.replace(word, '*' * len(word))
            new_text += f'{word} '
        new_text = new_text.replace(' .', '.')
        print(Panel(renderable=new_text,
                    padding=(2, 2), 
                    title="[reverse]Censored Text[/reverse]", 
                    border_style="bold violet",
                    box= box.DOUBLE_EDGE
            ))
          
        print(Panel(
            renderable=f"Offensive words censored:[bold red] {offensive_words} 😤[/bold red]",
            title="[reverse]Censored Words[/reverse]",
            
        ))


def censor_bad_words_not_strict(text: str) -> None:
    """
    Removes the bad words from the text and replaces them with asterisks partially and prints the censor text
    1. First we check if the text is a URL, if yes, then we parse the text from it and then use the model
    2. If the text is not a URL, then we directly use the model
    3. Remove the punctuations and convert text to lowercase
    4. Read the bad words from the file and store them in a list
    5. Split the text into words and for each word, we check if it is a bad word, if yes, then we partially replace it with asterisks
    6. Print the censored text and the number of bad words censored

    Args:
        text (str): text that needs to be censored
    """
      #----------------- Spinner -----------------#
    with Progress(
        SpinnerColumn(spinner_name="monkey", style="bold violet"),
        TextColumn("[progress.description]{task.description}", justify="left", style="bold cyan"),
        transient=True,
    ) as progress:
        progress.add_task(description="Censoring...", total=None)
    #----------------- Spinner -----------------#
    
        # check if the content is a URL, if yes, then parse the text from it and then use the model
        if isWebURL := check_url_or_text(text):
            print(Panel(title="[b reverse green]  Processing...  [/b reverse green]",
                        title_align="center",
                        padding=(1, 1),
                        renderable="URL detected 🌐")
                )
            text = parse_text_from_web(text)
            

        # if text and not URL, then directly use the model
        if not isWebURL:
            print(Panel(title="[b reverse yellow]  Warning!  [/b reverse yellow]",
                        title_align="center",
                        padding=(1, 1),
                        renderable="This is not a valid URL. Processing it as text... 📃")
                )
    

        with open('modules/_bad_words.txt', mode='r', encoding='utf-8') as f:
            bad_words = f.read().splitlines()
            bad_words_plural = [bad_words[i]+'s' for i in range(len(bad_words))]
            bad_words = bad_words + bad_words_plural
        
        
        text = cleanup_text(text)
        new_text = ''
        offensive_words = 0
        
        for word in text:
            word = str(word)
            if word.lower() in bad_words:
                offensive_words += 1
                if len(word) <= 3:
                    word = word.replace(word, '*' * len(word))
                elif len(word) <= 5:
                    # replace the middle character with asterisk
                    word = word.replace(word[1], '*')
                    word = word.replace(word[2], '*')
                    word = word.replace(word[3], '*')
                else:
                    word = word.replace(word[2:5], '***')
            new_text += f'{word} '
        new_text = new_text.replace(' .', '.')
        print(Panel(renderable=new_text,
                    padding=(2, 2), 
                    title="[reverse]Censored Text[/reverse]",
                    border_style="bold violet",
                    box= box.DOUBLE_EDGE
                    ))  
        print(Panel(renderable=f"Offensive words censored:[bold red] {offensive_words} 😤[/bold red] ",padding=(1, 1), title="[reverse]Censored Words[/reverse]"))


def readability_index(text: str) -> None:
    """
    Prints the readability index of the text and the summary of the index
    1. First we check if the text is a URL, if yes, then we parse the text from it and then use the model
    2. If the text is not a URL, then we directly use the model
    3. Remove the punctuations and convert text to lowercase
    4. Split the text into words and count the number of words
    5. Split the text into sentences and count the number of sentences
    6. The function then calculates the readability index using the textstat module and stores it in the "readability_index" variable.
    7. Print the readability index and the summary of the index

    Args:
        text (str): text to be analyzed
    """
       #----------------- Spinner -----------------#
    with Progress(
        SpinnerColumn(spinner_name="aesthetic", style="bold green"),
        TextColumn("[progress.description]{task.description}", justify="left", style="bold cyan"),
        transient=True,
    ) as progress:
        progress.add_task(description="Processing Text...", total=None)
    #----------------- Spinner -----------------#
    
        # check if the content is a URL, if yes, then parse the text from it and then use the model
        if isWebURL := check_url_or_text(text):
            print(Panel(title="[b reverse green]  Processing...  [/b reverse green]",
                        title_align="center",
                        padding=(1, 1),
                        renderable="URL detected 🌐")
                )
            text = parse_text_from_web(text)
            

        # if text and not URL, then directly use the model
        if not isWebURL:
            print(Panel(title="[b reverse yellow]  Warning!  [/b reverse yellow]",
                        title_align="center",
                        padding=(1, 1),
                        renderable="This is not a valid URL. Processing it as text... 📃")
                )
    
        #@atharva check this

        readability_index = textstat.flesch_reading_ease(text)

        if readability_index > 90:
            index_desc = "Very Easy"
        elif readability_index > 80:
            index_desc = "Easy"
        elif readability_index > 70:
            index_desc = "Fairly Easy"
        elif readability_index > 60:
            index_desc = "Standard"
        elif readability_index > 50:
            index_desc = "Fairly Difficult"
        elif readability_index > 30:
            index_desc = "Difficult"
        else:
            index_desc = "Very Confusing"

        print(Panel(
            title="[b reverse]Readability Index[/b reverse]", 
            title_align="center", 
            padding=(2, 2), 
            border_style="bold magenta1",
            box= box.DOUBLE,
            renderable=f"[b r blue]Lexicon Count[/b r blue]: {textstat.lexicon_count(text, removepunct=True)}\n\n[b r green]Character Count[/b r green]: {textstat.char_count(text)}\n\n[b r yellow2]Sentence Count[/b r yellow2]: {textstat.sentence_count(text)}\n\n[b r gold1]Words Per Sentence[/b r gold1]: {textstat.avg_sentence_length(text)}\n\n[b r white]Readability Index[/b r white]: {textstat.flesch_reading_ease(text)}")
            )


def extract_difficult_words(text: str) -> None:
    """
    Extracts the difficult words from the text and prints them, uses the _most_common_words.txt file to determine the difficult words
    1. First we check if the text is a URL, if yes, then we parse the text from it and then use the model
    2. If the text is not a URL, then we directly use the model
    3. Open the file with a list of simple words (most common words used in English).
    4. Clean up the text from any unnecessary characters, full stops, and convert it to lowercase.
    5. Calculate the word count of the text.
    6. Create a list of difficult words by filtering out all words that are in the list of simple words.
    7. Remove some common words that are not in the list of simple words.
    8. Remove duplicate words.
    9. Remove plurals of the same word.
    10. Remove plurals of which singular is in the simple words list.
    11. Sort the list of difficult words.
    12. Print the word count and the number of difficult words.
    13. Print the list of difficult words in columns.

    Args:
        text (str): text/url to be analyzed
    """
      #----------------- Spinner -----------------#
    with Progress(
        SpinnerColumn(spinner_name="aesthetic", style="bold gold1"),
        TextColumn("[progress.description]{task.description}", justify="left", style="bold white"),
        transient=True,
    ) as progress:
        progress.add_task(description="Extracting Tough Words...", total=None)
    #----------------- Spinner -----------------#
    
        # check if the content is a URL, if yes, then parse the text from it and then use the model
        if isWebURL := check_url_or_text(text):
            print(Panel(title="[b reverse green]  Processing...  [/b reverse green]",
                        title_align="center",
                        padding=(1, 1),
                        renderable="URL detected 🌐")
                )
            text = parse_text_from_web(text)

        # if text and not URL, then directly use the model
        if not isWebURL:
            print(Panel(title="[b reverse yellow]  Warning!  [/b reverse yellow]",
                        title_align="center",
                        padding=(1, 1),
                        renderable="This is not a valid URL. Processing it as text... 📃")
                )
            text = cleanup_text(text)
            text = ' '.join(text)

        with open(file='modules/_most_common_words.txt', mode='r', encoding='utf-8') as f:
            simple_words = f.read().splitlines()
        text = cleanup_text(text)
        article_word_count = len(text)

        # remove full stop from the words
        text = [word for word in text if '.' not in word]
        difficult_words = [word for word in text if word.lower() not in simple_words]
        filter_words = ['didnt', 'couldnt', 'wouldnt', 'shouldnt', 'isnt',
                        'wasnt', 'arent', 'werent', 'dont', 'doesnt', 'didnt', 'hasnt', 'hadnt']
        difficult_words = [
            word for word in difficult_words if word not in filter_words]
        # filter out duplicate words
        difficult_words = list(set(difficult_words))

        # remove plurals of the same word
        for word in difficult_words:
            if word[-1] == 's' and word[:-1] in difficult_words:
                difficult_words.remove(word)

        # remove plurals of which singular is in the simple words list
        for word in difficult_words:
            if word[-1] == 's' and word[:-1] in simple_words:
                difficult_words.remove(word)

        # TODO: Function has scope for imporvement (low value but high effort):
        # 1. Elminiate proper nouns -> Remove words that start with a capital letter but are not in the simple words list and not preceeded by a full stop. Because first word of a sentence is always capitalized.
        # 2. Remove gerunds (ing), past participles (ed) of the words that are in the simple words list. Those are not difficult words. (eg. "I am reading" -> "factories" is not detected as a difficult word but "factory" is.)

        difficult_words.sort()
        print(Panel(title="[b reverse navajo_white1]  Success!  [/b reverse navajo_white1]",
                    title_align="center",
                    padding=(1, 1),
                    border_style="navajo_white1",
                    box= box.DOUBLE,
                    renderable=f"Content Length: [bold blue]{article_word_count}[/bold blue] words\nExtracted [bold blue]{len(difficult_words)}[/bold blue] difficult words"),       
            )

        difficult_words = [
            Panel(f"[thistle1]{word}[thistle1]", expand=True, box=box.ROUNDED, border_style="pale_violet_red1")
            for word in difficult_words
        ]
         #----------------- Columns -----------------#

        print(Columns(difficult_words, equal=True, expand=True))

         #----------------- Columns -----------------#


def sentiment_score_to_summary(sentiment_score: int) -> str:
        """
        Converts the sentiment score to a summary of the score

        Args:
            sentiment_score (int): sentiment score

        Returns:
            str: summary of the sentiment score
        """

        if sentiment_score == 1:
            return "Extremely Negative"
        elif sentiment_score == 2:
            return "Somewhat Negative"
        elif sentiment_score == 3:
            return "Generally Neutral"
        elif sentiment_score == 4:
            return "Somewhat Positive"
        elif sentiment_score == 5:
            return "Extremely Positive"
            

          
def sentiment_analysis(content: str) -> None:
    """
    Performs sentiment analysis on the text and prints the sentiment score and the summary of the score
    1. Check if the content is a URL, if yes, then parse the text from it and then use the model
    2. If text and not URL, then directly use the model
    3. Clean up the text from any unnecessary characters, full stops, and convert it to lowercase.
    5. Load the tokenizer and model
    6. Encode the text using the tokenizer
    7. Send the encoded text to the model and get the result
    8. Take the highest value from the result and convert it to a summary
    9. Print the sentiment score and the summary

    Args:
        content (str): text/url to be analyzed
    """
          #----------------- Spinner -----------------#
    with Progress(
            SpinnerColumn(spinner_name="smiley", style="bold green"),
            TextColumn("[progress.description]{task.description}", justify="left", style="bold white"),
            transient=True,
        ) as progress:
        progress.add_task(description="Getting Sentiment...", total=None)
    #----------------- Spinner -----------------#

        # check if the content is a URL, if yes, then parse the text from it and then use the model
        if isWebURL := check_url_or_text(content):
            print(Panel(title="[b reverse green]  Processing...  [/b reverse green]",
                        title_align="center",
                        padding=(1, 1),
                        renderable="URL detected 🌐")
                )
            text = parse_text_from_web(content)

        # if text and not URL, then directly use the model
        if not isWebURL:
            print(Panel(title="[b reverse yellow]  Warning!  [/b reverse yellow]",
                        title_align="center",
                        padding=(1, 1),
                        renderable="This is not a valid URL. Processing it as text... 📃")
                )
            text = cleanup_text(content)
            text = ' '.join(text)

     

        tokenizer = AutoTokenizer.from_pretrained(
            "nlptown/bert-base-multilingual-uncased-sentiment")
        model = AutoModelForSequenceClassification.from_pretrained(
            "nlptown/bert-base-multilingual-uncased-sentiment")
        tokens = tokenizer.encode(
            text, return_tensors='pt', truncation=True, padding=True)
        result = model(tokens)
        result.logits
        sentiment_score = int(torch.argmax(result.logits))+1
        outcome = sentiment_score_to_summary(sentiment_score)
        if outcome in ["Extremely Negative", "Somewhat Negative"]:
            emoji = "😞"
        
        elif outcome == "Generally Neutral":
            emoji = "😐"
            
        elif outcome in ["Somewhat Positive", "Extremely Positive"]:
            emoji = "😀"
        
        print(Panel(title="[b reverse green]  Success!  [/b reverse green]",
                        title_align="center",
                        padding=(1, 1),
                        renderable=f"Sentiment Analysis Verdict: {sentiment_score_to_summary(sentiment_score)} {emoji}") 
                )
       

# TODO @atharva check this
def summarize_text_util(text:str, per:int)->str:
    """
    Summarizes the text using the spacy library
    1. Load the document in Spacy
    2. Create a list of tokens (i.e. each word in the document)
    3. Create a dictionary of the words and their frequency
    4. Get the maximum frequency of a word
    5. Divide each frequency by the maximum frequency
    6. Create a list of sentence tokens (i.e. each sentence in the document)
    7. Create a dictionary of the sentences and their score
    8. Multiply each sentence's score by the frequency of each word in that sentence
    9. Get the number of sentences to include in the summary (here 20% of the sentences in the document)
    10. Get the top sentences with the highest score
    11. Combine the words in the top sentences into a string
    
    Args:
        text (str): text to be summarized
        per (int): percentage of the text to be summarized

    Returns:
        str: summarized text
    """
   
    nlp = spacy.load('en_core_web_sm')
    doc = nlp(text)
    tokens = [token.text for token in doc]
    word_frequencies = {}
    for word in doc:
        if (
            word.text.lower() not in list(STOP_WORDS)
            and word.text.lower() not in punctuation
        ):
            if word.text in word_frequencies:
                word_frequencies[word.text] += 1
            else:
                word_frequencies[word.text] = 1

    max_frequency = max(word_frequencies.values())
    for word in word_frequencies:
        word_frequencies[word] = word_frequencies[word]/max_frequency
    sentence_tokens = list(doc.sents)
    sentence_scores = {}
    for sent in sentence_tokens:
        for word in sent:
            if word.text.lower() in word_frequencies:
                if sent in sentence_scores:
                    sentence_scores[sent] += word_frequencies[word.text.lower()]
                else:
                    sentence_scores[sent] = word_frequencies[word.text.lower()]
    select_length = int(len(sentence_tokens)*per)
    summary = nlargest(select_length, sentence_scores, key=sentence_scores.get)
    final_summary = [word.text for word in summary]
    summary = ''.join(final_summary)
    return summary


def summarize_text(content: str, file: Optional[bool] = False) -> None:
    """
    Print the summarized text or internet article. 
    1. Check if the content is a URL or text
    2. If URL, then parse the text from it and then use the model
    3. If text, then directly use the model
    4. Clean up the text from any unnecessary characters, full stops, and convert it to lowercase.
    5. It summarizes the text using the summarize_text_util function.
    6. If the input is a URL, it prints the headline of the article as well.
    7. If the output is a file, it saves the summary to a file called summary.txt. 

    Args:
        text (str): Text that is to be summarized
    """

     #----------------- Spinner -----------------#
    with Progress(
            SpinnerColumn(spinner_name="dots12", style="bold blue"),
            TextColumn("[progress.description]{task.description}", justify="left", style="bold white"),
            transient=True,
        ) as progress:
        progress.add_task(description="Summarizing...", total=None)
    #----------------- Spinner -----------------#
    
        if isWebURL := check_url_or_text(content):
            print(Panel(title="[b reverse green]  Processing...  [/b reverse green]",
                        title_align="center",
                        padding=(1, 1),
                        renderable="URL detected 🌐")
                )

            # this is just get the headings
            r = requests.get(content)
            soup = BeautifulSoup(r.content, "html.parser")
            headline = soup.find('h1').get_text()

            # this gets the body of the article.
            text = parse_text_from_web(content)

        # if text and not URL, then directly use the model
        if not isWebURL:
            print(Panel(title="[b reverse yellow]  Warning!  [/b reverse yellow]",
                        title_align="center",
                        padding=(1, 1),
                        renderable="This is not a valid URL. Processing it as text... 📃")
                )
            text = cleanup_text(content)
            text = ' '.join(text)

        text_summary = summarize_text_util(text, 0.2)

        if not file: #@atharva check this
            if isWebURL:
                print(Panel(title="[b reverse green]  Success!  [/b reverse green]",
                        title_align="center",
                        padding=(1, 1),
                        renderable=f"Length of the article: {len(text)} characters  \n\n Length of the summary:{len(text_summary)} characters \n\nHeadline:\n{headline} \n\n Summary:\n{text_summary}"
                ))
            else:
                print(Panel(title="[b reverse green]  Success!  [/b reverse green]",
                        title_align="center",
                        padding=(1, 1),
                        renderable=f"Length of the article: {len(text)} characters  \n\n Length of the summary:{len(text_summary)} characters \n\n Summary:\n{text_summary}"
                ))

        if file:  
            # writing to a .txt file
            with open("summary.txt", "w", encoding="utf-8") as f:
                f.write(f"Length of the article: {len(text)} characters\n\n")
                f.write(f"Length of the summary:{len(text_summary)} characters\n\n")
                if isWebURL:
                    f.write(str(f"Headline:\n{headline}\n\n"))
                f.write("------------------------------------------------------------\n\n")
                f.write(f"Summary:\n{text_summary}\n\n")

            print(Panel(title="[b reverse green]  Summary Exported!  [/b reverse green]",
                        title_align="center",
                        padding=(1, 1),
                        renderable="[bold green]Summary saved[/bold green] to [bold]summary.txt[/bold]")
              )
        #TODO: writing to a .md file
       