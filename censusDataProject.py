def populateGeoCodes():

    # Builds state & county database with IDs from datausa.io. It can be interrupted and will look for spot to
    # resume to simulate crawling of bigger database. Probably not necessary in this case but mostly to train building
    # restartable crawler.
    #
    # state 	04000US 	US States (including D.C. and Puerto Rico)
    # county 	05000US 	US Counties
    #
    import sqlite3
    import urllib.request, urllib.error, urllib.parse
    import ssl
    import json
    import requests

    #Ignore SSL certificate errors
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    dataBase = sqlite3.connect("censusData.db")
    db= dataBase.cursor()
    db.executescript("""
        create table if not exists States (id int unique primary key, name varchar unique); 
        create table if not exists Counties (id int unique primary key, name varchar unique, state_ID int);
    """)

    stateDBcount = db.execute("select count(*) from States").fetchone()[0] #check if all states +PR/DC already in database
    if stateDBcount<52:
        print("Getting state list from datausa.io")
        statesURL = "https://api.datausa.io/attrs/geo/01000US/children/"
        dataJSON = requests.request("get", statesURL).json()
        extractedList = dataJSON["data"]
        for loc in extractedList:
            newloc = loc[1]
            newLongID = loc[0]
            newID = newLongID[7:]
            db.execute("insert or replace into States (id, name) values (?, ?)", (newID, newloc))
        db.execute("commit")

    #Loop through each state, check whether counties are present and re-start at the previous state (making sure the
    #previous state has not been interrupted
    db.execute("select id from States order by id")
    startState = "not found"
    prevStateID = None
    stateList = list()
    for stateID in db.fetchall(): #make list with stateIDs that still need to download counties
        db.execute("select count(*) from Counties where state_ID=(?)", (stateID[0],))
        if db.fetchone()[0] > 0: #at least some counties already added, skip loop
            prevStateID = stateID[0]
            continue #at least some counties already added
        if startState == "not found" and prevStateID is not None: #First state were nothing has been added. Go back one if not first and add that one in case it was interrupted there
            startState = "found"
            stateList.append(prevStateID)
        stateList.append(stateID[0])
        startState = "found"

    baseURL = "https://api.datausa.io/attrs/geo/"
    for stateID in stateList:
        print(f"Retrieving County codes for {stateID} from DataUSA.io")
        stateSpecURL = "04000US" + stateID + "/children/"
        countyURL = baseURL + stateSpecURL
        countyJSON = requests.request("get", countyURL).json()
        extractedCounties = countyJSON["data"]

        for county in extractedCounties:
            countyLongID = county[0]
            countyID = countyLongID[7:]
            countyName = county[1]
            if "," in countyName:
                countyName = countyName[0:-4]
            if "'" in countyName:
                countyName = countyName.replace("'","")
            db.execute("insert or replace into Counties (id, name, state_ID) values (?,?,?)", (countyID,countyName,stateID))
        db.execute("commit")
    print("State and County codes stored in local database")
# populateGeoCodes()

def insertTitleInHTMLFile(chartTitle):
    # rawDataCollector()#
    import re

    # replaces title in file: lineGraphData.htm in line:
    # var options = {title: 'Sakai Developer Email Participation by Organization'};

    fileHandle = open("lineGraphData.htm","r+")
    file = fileHandle.read()
    oldChartTitle = re.findall("title: '.*?'", file)
    newFile = file.replace(oldChartTitle[0], f"title: '{chartTitle}'")
    fileHandle.truncate(0)
    fileHandle.write(newFile)
    fileHandle.close()

def displayData(geoLevel, dataKind):
    # insertTitleInHTMLFile("Blearg")
    import sqlite3

    # Exports data to lineGraphData.js, which lineGraphData.htm uses to display data.
    # Code for lineGraphData kindly provided by Dr. Charles Severance (Univ. of Michigan)
    # lineGraphData.js structure:
    # gline = [ ['X value title','series1 title','series2 title','series3 title'],
    # ['X1 value',Series1 Y1 value,Series2 Y1 value, Series3 Y1 value],
    # ['X2 value',Series1 Y2 value,Series2 Y2 value, Series3 Y2 value],
    # ['X3 value',Series1 Y3 value,Series2 Y3 value, Series3 Y3 value],
    # ];


    import webbrowser
    database = sqlite3.connect("censusData.db")

    # connect to databases, json file and find out how many years worth of data are present
    # and write into years list
    db = database.cursor()
    db.execute(f"pragma table_info({dataKind}Data)")
    years = list()
    for column in db.fetchall():
        years.append(column[1])
    years.remove(years[0])
    fileHandle = open("lineGraphData.js", "w")
    fileHandle.write("gline = [ \n['Years'")
    if geoLevel =="nation":
        db.execute(f"select * from {dataKind}Data where locID=0")
        fileHandle.write(",'USA']\n")
        counter = 0
        for column in db.fetchone()[1:]:
            fileHandle.write(",['" + str(years[counter]) + "'," + str(column) +"]\n")
            counter += 1
    else:
        if geoLevel =="state":
            db.execute(f"select States.name, {dataKind}Data.* from States join {dataKind}Data on States.id={dataKind}Data.locID")
        if geoLevel == "county":
            db.execute(f"select Counties.name, {dataKind}Data.* from Counties join {dataKind}Data on Counties.id={dataKind}Data.locID")
        dataDic = dict()
        dataDic["name"]=list()
        for year in years:
            dataDic[year]=list()
        for row in db.fetchall():
            dataDic["name"].append(row[0])
            counter=2
            for year in years:
                dataDic[year].append(row[counter])
                counter += 1
        for name in dataDic["name"]:
            fileHandle.write(f",'{name}'")
        fileHandle.write("],\n")
        for year in years:
            fileHandle.write(f"['{year}'")
            for dataPoint in dataDic[year]:
                if dataPoint is None:
                    dataPoint = 0
                fileHandle.write(f",{dataPoint}")
            fileHandle.write("],\n")

    fileHandle.write("];")
    insertTitleInHTMLFile(dataKind + " by " + geoLevel)
    webbrowser.open("lineGraphData.htm")
    print("Displaying results in your web browser")
# displayData("state","pop")

def rawDataCollector():
    # get data from datausa.io. USA census data and dump in sql database rawCensusData.db
    # https://api.datausa.io/api?show=geo&sumlevel=nation&required=pop
    # Basic API description: https://datausa.io/about/api/
    # Atributes description (github): https://github.com/DataUSA/datausa-api/wiki/Attribute-API

    import sqlite3
    import json
    import urllib.request, urllib.parse, urllib.error
    import ssl
    import requests

    #Ignore SSL certificate errors
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    #input and input validation
    dataKind = input("What kind of data are you looking for (see dataUSA github API description for attributes)? ")
    geoConstraint = input("What geography do you want to look at (nation, state or county level)? ")
    # Make sure inputs are valid:
    if len(geoConstraint) < 1: #set default geography to nation
        geoConstraint = "nation"
    if geoConstraint != "nation" and geoConstraint !="state" and geoConstraint != "county":
        print("Error: geography is limited to nation, state or county. Displaying nation wide data")
        geoConstraint="nation"
    if len(dataKind) < 1:  #Set default data kind to population
        dataKind = "pop"
    #query api at nation level (lowest data usage) with data kind to make sure there's a response
    requestURL=f"https://api.datausa.io/api/?show=geo&required={dataKind}&sumlevel=nation"
    dataJSON = requests.request("Get", requestURL).json()
    try:
        extractedJSON = dataJSON["data"]
    except:
        print(f"No data found for your query of {dataKind}. Try looking up possible parameters at API github page at https://github.com/DataUSA/datausa-api/wiki/Data-API#params")
        quit()

    populateGeoCodes()
    database = sqlite3.connect("censusData.db")
    db = database.cursor()

    db.execute(f"create table if not exists {dataKind}Data (locID int unique primary key)")
    db.execute(f"select count(*) from {dataKind}Data")
    locationsList = ["nation","state", "county"]
    # check whether this data kind has already been retrieved, if no get it at all levels (for simplicity)
    if db.fetchone()[0]==0:
        print("Requested Data not found in local database. Retrieving requested data from dataUSA.io API")
        baseURL = "https://api.datausa.io/api?show=geo&" #sumlevel=nation&required=pop
        for location in locationsList:
            requestDic={"sumlevel":location,"required":dataKind}
            requestURL = baseURL + urllib.parse.urlencode(requestDic)
            dataJSON = requests.request("Get", requestURL).json()
            extractedJSON = dataJSON["data"]
            for dataSet in extractedJSON:
                year = "[" + str(dataSet[0]) + "]"
                loc = dataSet[1][7:]
                if loc == "":
                    loc = 0 # nationwide
                requestedValue = dataSet[2]
                try:
                    db.execute(f"select {year} from {dataKind}Data") #This is just to cause an error if column does not exist to then add it
                except:
                    db.execute(f"alter table {dataKind}Data add {year} int")
                db.execute(f"insert or ignore into {dataKind}Data (locID,{year}) values(?,?)", (loc,requestedValue))
                db.execute(f"UPDATE {dataKind}Data SET {year}=? WHERE locID=?", (requestedValue, loc))
            db.execute("commit")
    displayData(geoConstraint,dataKind)
rawDataCollector()
