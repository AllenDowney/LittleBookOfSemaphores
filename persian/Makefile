LATEX = xelatex

PDFFLAGS = -dCompatibilityLevel=1.4 \
           -dCompressPages=true -dUseFlateCompression=true  \
           -dEmbedAllFonts=true -dSubsetFonts=true -dMaxSubsetPct=100

NAME = LittleBookOfSemaphores

OS:=$(shell uname || echo unknown)
ifeq ($(OS), Linux)
    OPEN:=xdg-open
endif
ifeq ($(OS), Darwin)
    OPEN:=open
endif
ifeq ($(OS), unknown)
    OPEN:=echo
endif


all: book.tex
	${LATEX} $<
	bibtex $(basename $<)
	makeindex $(basename $<)
	${LATEX} $<
	${LATEX} $<
	$(OPEN) $(basename $<).pdf &> /dev/null &

FILES = book.tex book.bib table.eps

distrib:
	ps2pdf $(PDFFLAGS) $(NAME).ps $(NAME).pdf
	cp $(NAME).* /home/downey/public_html/greent/semaphores

clean:
	rm -fv *.{aux,log,dvi,idx,ilg,ind,toc,out,pyg,bbl,blg}
