# censusData
Training project using an SQL database with python and retrieving and visualizing census data from the dataUSA API

Wrote this to get some practice manipulating SQL database (SQLite3) with python, webcrawling and very primitive data visualization. There is virtually no practical use to it since the dataUSA.io website has way nicer display options. Limited to county level at the lowest but can easily be enhanced just using the same methods to lower levels but I felt I learned what I wanted to. Also needs some error catching for some incomplete data sets but again I feel I know how to do it and don't feel I would learn much more with the repetition. 

rawDataCollector:
Check whether data is already present in local database, if not get data from datausa.io. USA census data and dump in sql database censusData.db then calls displayData
displayData:
Reads database data and inserts it into a dictionary so that it can be written in the right syntax and order to a json file, which in turn is used by an html file to visualize the data. The HTML file was written by (I believe) Dr. Charles Severance and uses Google gline visualization library.
