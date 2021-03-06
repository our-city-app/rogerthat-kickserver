# Content of this file was based on example found at
# http://butterfat.net/wiki/Documentation/TwistedJabberComponentExample
import os

from twisted.application import service
from twisted.internet import reactor
from twisted.web import resource, server
from twisted.web.client import Agent, HTTPConnectionPool
from twisted.words.protocols.jabber import component

import callbackec
import kickec
from apns import ApplePushConnectionFactory
from callbackec import IpToCountryResource, CallbackResource
from callbackec import RegisterResource
from callbackec import StartFlowResource
from callbackec import UnRegisterResource
from configuration import APP_ENGINE_SECRET, XMPP_SERVICE_NAME, KICK_SERVICE, PASSWORD, ADDRESS, \
    XMPP_RECONNECT_INTERVAL, APNS_ENABLED, CALLBACK_SERVICE, WEBSERVICE_PORT, configuration
from kickec import KickResource
from mccommon import LogService
from util import ServerTime, HighLoadTCPServer

# Let's get started
application = service.Application('Rogerthat cloud servicer')

# One single agent to perform outbound http requests ===> HTTP/1.1 Connection pooling
pool = HTTPConnectionPool(reactor)
agent = Agent(reactor, pool=pool)
serverTime = ServerTime(agent)

# Set up kick jabber component
sm = component.buildServiceManager("kick.%s" % configuration[XMPP_SERVICE_NAME], configuration[KICK_SERVICE][PASSWORD], (configuration[KICK_SERVICE][ADDRESS]))
sm.getFactory().maxDelay = configuration[XMPP_RECONNECT_INTERVAL]
LogService().setServiceParent(sm)

kickService = kickec.KickService()
kickService.setHTTPAgent(agent)
kickService.setAppEngineSecret(configuration[APP_ENGINE_SECRET])
if configuration[APNS_ENABLED] is True:
    # Create Push & Feedback Service Factory
    applePushConnectionFactory = ApplePushConnectionFactory(agent, configuration[APP_ENGINE_SECRET], serverTime, application)
    kickService.setApplePushNotificationServiceClientFactory(applePushConnectionFactory)

kickService.setServiceParent(sm)
sm.setServiceParent(application)

# Set up callback jabber component
sm = component.buildServiceManager("callback.%s" % configuration[XMPP_SERVICE_NAME], configuration[CALLBACK_SERVICE][PASSWORD], (configuration[CALLBACK_SERVICE][ADDRESS]))
sm.getFactory().maxDelay = configuration[XMPP_RECONNECT_INTERVAL]
LogService().setServiceParent(sm)

callbackService = callbackec.CallbackService()
callbackService.setHTTPAgent(agent)
callbackService.setAppEngineSecret(configuration[APP_ENGINE_SECRET])
callbackService.setServiceParent(sm)

sm.setServiceParent(application)

# Set up web resources
root = resource.Resource()
root.putChild('callback', CallbackResource(callbackService, configuration[APP_ENGINE_SECRET], serverTime))
root.putChild('unregister', UnRegisterResource(configuration[APP_ENGINE_SECRET], serverTime))
root.putChild('register', RegisterResource(configuration[APP_ENGINE_SECRET], serverTime))
root.putChild('kick', KickResource(kickService, configuration[APP_ENGINE_SECRET], serverTime))
root.putChild('start_flow', StartFlowResource(configuration[APP_ENGINE_SECRET], serverTime, agent))
root.putChild('ip2country', IpToCountryResource(configuration[APP_ENGINE_SECRET], serverTime))

webservice_port = int(os.environ.get('WEBSERVICE_PORT', configuration[WEBSERVICE_PORT]))
webservice = HighLoadTCPServer(webservice_port, server.Site(root), request_queue_size=100)
webservice.setServiceParent(application)
