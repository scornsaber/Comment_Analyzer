import sys
import pyqtgraph as pg
import matplotlib.pyplot as plt #might not be used
from PyQt6.QtWidgets import QApplication,QWidget,QLineEdit, QMainWindow, QLabel, QVBoxLayout, QPushButton
from youtube_comments_jsonl import get_comments 
from googleapiclient.discovery import build
from langdetect import detect, DetectorFactory, LangDetectException
import json
# Required installations 
# pip install google-api-python-client langdetect
# pip install pytube
# pip install pytubefix 
# pip instakk pyQt6


from pytubefix import YouTube,extract


# Run and save to JSONL
def saveToFile(VIDEO_ID):
    comments_data = get_comments(VIDEO_ID)

    with open('youtube_comments.jsonl', 'w', encoding='utf-8') as f:
        for comment in comments_data:
            f.write(json.dumps(comment, ensure_ascii=False) + '\n')

    print(f"Saved {len(comments_data)} comments to youtube_comments.jsonl")




#Main window
class MainWindow(QMainWindow): 
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Comment Analyzer")
        self.resize(1200, 600) # Set initial size
        self.center_on_screen() #Center the window

        #All these have "self" next to them so they can be called outside of here.
        self.linkPrompt = QLabel(self)
        self.commentsAnalyzed= QLabel(self) #Return number of comments analyzed (Need some way to count them)
        self.sentimentReturn = QLabel(self) #Return sentiment summary
        self.linkReturn = QLabel(self) #Read link back to user
        self.linkReturn.setWordWrap(True) #Prevents text from going off-screen
        self.sentimentReturn.setWordWrap(True)

       #buttons
        self.submitButton=QPushButton(self)
        self.backButton=QPushButton(self)

        
        self.inputLink=QLineEdit(self) #input box for the video link
        self.plot_graph = pg.PlotWidget(self) #graph, just a stant-in for now
        
        #input prompt
        self.linkPrompt.setText("Please enter a Youtube Video Link:")
        font = self.linkPrompt.font()
        font.setPointSize(15)
        self.linkPrompt.setFont(font)
        self.linkPrompt.setGeometry(10,-100,500,500) 
     
        #input link
        self.inputLink.setPlaceholderText("Enter a video link")
        self.inputLink.setGeometry(320,100,450,75) #(100 units from the top)
      
        #submit button
        self.submitButton.setGeometry(775, 100, 125,75)
        self.submitButton.setText("Submit")
        self.submitButton.clicked.connect(self.submit_button_clicked)

        #back button 
        self.backButton.setGeometry(600, 500, 125,75)
        self.backButton.setText("Enter a new link")
        self.backButton.clicked.connect(self.back_button_clicked)

        #hide the back button when not needed.
        self.backButton.hide()

#Get video title
    def videoTitle(self): 
           try:
             video= YouTube(self.inputLink.text())
             return video.title
           except Exception as e:
               return "Error, could not retrieve video title"

    #Get video id
    def videoID(self): 
           try:
             video= YouTube(self.inputLink.text())
             id=extract.video_id(self.inputLink.text())
             return id
           #If a video cannot be found from the input
           except Exception as e:
               return "Invalid"

    #Get the video's author
    def videoAuthor(self): 
           try:
             author= YouTube(self.inputLink.text())
             return author.author
           except Exception as e:
               return "Error, could not retrieve video title"


#submit button actions
    def submit_button_clicked(self):
        VIDEO_ID=self.videoID() 
        if (VIDEO_ID!="Invalid"): 
            videoName=self.videoTitle()
            author = self.videoAuthor()

            #show everything 
            self.linkReturn.show()
            self.sentimentReturn.show()

            #Text change
            self.linkReturn.setText(f"From this video: {videoName} with the ID {VIDEO_ID} by {author}") 
            font = self.linkReturn.font()
            font.setPointSize(15)
            self.linkReturn.setFont(font)
            self.linkReturn.setGeometry(10,-200,700,500) 

            #Return comment sentiment
            self.sentimentReturn.setText(f"The general sentiment of the comments is:")
            font = self.sentimentReturn.font()
            font.setPointSize(15)
            self.sentimentReturn.setFont(font)
            self.sentimentReturn.setGeometry(10,-100,500,500) 

             #Hiding other stuff to prevent screen cluttering
            self.inputLink.hide()
            self.submitButton.hide()
            self.linkPrompt.hide()
            #show graph. it's just a stand-in for now. Will later likely replace with a bar graph. 
            self.graphSentiment()
            saveToFile(VIDEO_ID) #Collect comments from video and put into a file 
            
            self.backButton.show()

        else: 
            print("Invalid input")



#return to original screen
    def back_button_clicked(self):
         self.plot_graph.hide()
         self.inputLink.show()
         self.submitButton.show()
         self.linkPrompt.show()
         self.linkReturn.hide()
         self.sentimentReturn.hide()
         self.backButton.hide()

#Draws a graph, for now it is a random graph though. 
    def graphSentiment(self):
        self.plot_graph.show()
        self.plot_graph.setGeometry(750,100,400,500)
        self.plot_graph.setBackground("w")
        item1 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        item2 = [30, 32, 34, 32, 33, 31, 29, 32, 35, 30]
        self.plot_graph.plot(item1, item2)

#Center the window 
    def center_on_screen(self):
        frame_geometry = self.frameGeometry()
        screen_center = self.screen().availableGeometry().center()
        frame_geometry.moveCenter(screen_center)
        self.move(frame_geometry.topLeft())

#execute everything
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

