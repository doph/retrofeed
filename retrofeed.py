import os
import yaml

# import all the feed classes, these will be available in the global namespace
from feeds import *

def construct_sequence():
    # Load the configuration file
    with open('config.yaml', 'r') as f:
        cfg = yaml.load(f, Loader=yaml.FullLoader)

    # Construct the sequence of feeds
    sequence = []
    instances = {}
    for feed in cfg['sequence']:
        if feed in instances.keys():
            # If the feed has already been instantiated, add the existing instance to the sequence
            sequence.append(instances[feed])
        else:
            # get the dictionary named by the sequence feed
            feed_config = cfg[feed]
            # find the Class object named by the feed_class key
            feed_class = globals()[feed_config['feed_class']]
            # Create a new instance of the specified feed class
            feed_instance = feed_class(feed_config)
            # Add the instance to the dictionary of instances
            instances[feed] = feed_instance
            # Add the instance to the sequence
            sequence.append(feed_instance)

    return sequence

def main():
    feed_sequence = construct_sequence()

    os.system('clear')

    title = Title()
    title.show()

    # Main loop
    while True:
        for feed in feed_sequence:
            feed.show()
        

# __main__ is the entry point for the program when invoked from the command line
if __name__ == "__main__":
    main()
