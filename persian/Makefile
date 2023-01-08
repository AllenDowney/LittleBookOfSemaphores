LATEX = latex

DVIPS = dvips

PDFFLAGS = -dCompatibilityLevel=1.4 \
           -dCompressPages=true -dUseFlateCompression=true  \
           -dEmbedAllFonts=true -dSubsetFonts=true -dMaxSubsetPct=100

NAME = LittleBookOfSemaphores

all:	book.tex
	xelatex book
	bibtex book
	makeindex book
	#dvips -Ppdf -o $(NAME).ps book
	evince book.pdf &> /dev/null & #$(NAME).ps 

FILES = book.tex book.bib table.eps

distrib: 
	ps2pdf $(PDFFLAGS) $(NAME).ps $(NAME).pdf
	cp $(NAME).* /home/downey/public_html/greent/semaphores

clean:
	rm -fv *.aux *.log *.dvi *.idx *.ilg *.ind *.toc *.out *.pyg *.bbl *.blg
