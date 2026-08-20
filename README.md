# LittleBookOfSemaphores

LaTeX source and supporting code for The Little Book of Semaphores, by Allen Downey.

## Development environment (conda / mamba)

For a reproducible setup (recommended for Sync development and tests):

```bash
make create_environment_dev
conda activate LittleBookOfSemaphores
```

Useful targets: `make help`, `make tests`, `make update_environment_dev`, `make delete_environment`.

Pip-only equivalent for CI: `pip install -r requirements-dev.txt` (still needs system tkinter to run the desktop GUI).

## Running Sync

Desktop Sync needs Python with tkinter (`tk` is included in the conda environment above).

From a zip download:

1. [Download this repository in a Zip file](https://github.com/AllenDowney/LittleBookOfSemaphores/archive/refs/heads/master.zip)

2. Unzip the zip file

```
unzip LittleBookOfSemaphores-master.zip
```

3. Change into the directory that contains Sync.py

```
cd LittleBookOfSemaphores-master/code/
```

4. Run Sync without example code:

```
python Sync.py
```

5. Run Sync with example code:

```
python Sync.py sync_code/barrier.py
```

If you are using Anaconda, you might find that the fonts don't look good. This is a well-known problem with no easy solution.

See [`PROJECT_BOARD.md`](PROJECT_BOARD.md) for the Sync web-app roadmap.

## Translations

The following list of translations is sorted alphabetically.

- [Hungarian](https://github.com/bodri5/LittleBookOfSemaphoresHungarian)
- [Persian](https://github.com/ircsbook/LittleBookOfSemaphores)

### EPUB Versions

- [English](epub/TheLittleBookOfSemaphores.epub)
- [Portuguese (Brazil)](epub/TheLittleBookOfSemaphores-PTBR.epub)

If you have created a translation of this book and would like to add it to this list, feel free to submit a pull request or contact me to include it here.
