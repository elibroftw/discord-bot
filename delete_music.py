from shutil import rmtree
from os import mkdir

print('Deleting Music Directory... ')
rmtree('music')
print('Creating Music Directory...')
mkdir('music')
print('Done!')