from shutil import rmtree
from os import mkdir

print('Deleting Music Directory... ')
rmtree('Music')
print('Creating Music Directory...')
mkdir('Music')
print('Done!')