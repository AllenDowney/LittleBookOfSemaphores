LATEX = latex

DVIPS = dvips

PDFFLAGS = -dCompatibilityLevel=1.4 \
           -dCompressPages=true -dUseFlateCompression=true  \
           -dEmbedAllFonts=true -dSubsetFonts=true -dMaxSubsetPct=100

all:	sem.tex
	latex sem
	bibtex sem
	makeindex sem
	dvips -Ppdf -o downey08semaphores.ps sem
	evince downey08semaphores.ps

FILES = sem.tex sem.bib table.eps

distrib: 
	ps2pdf $(PDFFLAGS) downey08semaphores.ps downey08semaphores.pdf
	tar -cf downey08semaphores.tar $(FILES)
	tar -czf downey08semaphores.tgz $(FILES)
	cp downey08semaphores.* /home/downey/public_html/greent/semaphores
