from bokeh.server.server import Server

server = Server(
    bokeh_applications,  # list of Bokeh applications
    io_loop=loop,        # Tornado IOLoop
    **server_kwargs      # port, num_procs, etc.
)

# start timers and services and immediately return
server.start()