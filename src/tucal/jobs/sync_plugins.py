
import tucal.plugins

if __name__ == '__main__':
    plugins = tucal.plugins.plugins()
    for course, p in plugins:
        p.sync()
