#!/usr/bin/python3
# ============================================================================
# Tom Slee, 2013--2017.
#
# An ABSurvey is a scrape of the Airbnb web site, which may also collect
# information about listings. There are several survey types:
# - neighborhood (-s)
# - bounding box (-sb)
# - zipcode (-sz)
# See the README for which to use.
# ============================================================================
import logging
import sys
import random
import psycopg2
import time
from datetime import date
from bs4 import BeautifulSoup
import json
from airbnb_listing import ABListing
import airbnb_ws

logger = logging.getLogger()


class Timer:
    def __enter__(self):
        self.start = time.clock()
        return self

    def __exit__(self, *args):
        self.end = time.clock()
        self.interval = self.end - self.start


class ABSurvey():
    """
    Class to represent a generic survey, using one of several methods.
    Specific surveys (eg bounding box, neighbourhood) are implemented in
    subclasses. Right now (May 2018), however, only the bounding box survey
    is working.
    """

    def __init__(self, config, survey_id):
        self.config = config
        self.survey_id = survey_id
        self.search_area_id = None
        self.search_area_name = None
        self.set_search_area()
        self.room_types = ["Private room", "Entire home/apt", "Shared room"]

        # Set up logging
        logger.setLevel(config.log_level)

        # create a file handler
        logfile = "public/survey-{survey_id}.log".format(
            survey_id=self.survey_id)
        filelog_handler = logging.FileHandler(logfile, encoding="utf-8")
        filelog_handler.setLevel(config.log_level)
        filelog_formatter = logging.Formatter(
            '%(asctime)-15s %(levelname)-8s%(message)s')
        filelog_handler.setFormatter(filelog_formatter)

        # logging: set log file name, format, and level
        logger.addHandler(filelog_handler)

        # Suppress informational logging from requests module
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logger.propagate = False

    def set_search_area(self):
        """
        Compute the search area ID and name.
        """
        try:
            conn = self.config.connect()
            cur = conn.cursor()
            cur.execute("""
                select sa.search_area_id, sa.name
                from search_area sa join survey s
                on sa.search_area_id = s.search_area_id
                where s.survey_id = %s""", (self.survey_id,))
            (self.search_area_id, self.search_area_name) = cur.fetchone()
            cur.close()
        except (KeyboardInterrupt, SystemExit):
            cur.close()
            raise
        except Exception:
            cur.close()
            logger.error("No search area for survey_id " + str(self.survey_id))
            raise

    def update_survey_entry(self, search_by):
        try:
            survey_info = (date.today(),
                           search_by,
                           self.survey_id, )
            sql = """
            update survey
            set survey_date = %s, survey_method = %s
            where survey_id = %s
            """
            conn = self.config.connect()
            cur = conn.cursor()
            cur.execute(sql, survey_info)
            return True
        except psycopg2.Error as pge:
            logger.error(pge.pgerror)
            cur.close()
            conn.rollback()
            return False

    def listing_from_search_page_json(self, json, room_id):
        """
        Some fields occasionally extend beyond the varchar(255) limit.
        """
        try:
            listing = ABListing(self.config, room_id, self.survey_id)
            # listing
            json_listing = json["listing"] if "listing" in json else None
            # print(json_listing)
            json_pricing = json["pricing_quote"] if "pricing_quote" in json else None
            # print("O JSON LISTING: ", json_pricing)
            if json_listing is None:
                return None
            if "room_type" in json_listing:
                listing.room_type = json_listing["room_type"]
            else:
                listing.room_type = None
            if "user" in json_listing:
                listing.host_id = json_listing["user"]["id"]
            else:
                listing.host_id = None
            if "public_address" in json_listing:
                listing.address = json_listing["public_address"]
            else:
                listing.address = None
            if "reviews_count" in json_listing:
                listing.reviews = json_listing["reviews_count"]
            else:
                listing.reviews = None
            if "star_rating" in json_listing:
                listing.overall_satisfaction = json_listing["star_rating"]
            else:
                listing.overall_satisfaction = None
            if "person_capacity" in json_listing:
                listing.accommodates = json_listing["person_capacity"]
            else:
                listing.accommodates = None
            if "bedrooms" in json_listing:
                listing.bedrooms = json_listing["bedrooms"]
            else:
                listing.bedrooms = None
            if "bathrooms" in json_listing:
                listing.bathrooms = json_listing["bathrooms"]
            else:
                listing.bathrooms = None
            if "lat" in json_listing:
                listing.latitude = json_listing["lat"]
            else:
                listing.latitude = None
            if "lng" in json_listing:
                listing.longitude = json_listing["lng"]
            else:
                listing.longitude = None
            # The coworker_hosted item is missing or elsewhere
            if "coworker_hosted" in json_listing:
                listing.coworker_hosted = json_listing["coworker_hosted"]
            else:
                listing.coworker_hosted = None
            # The extra_host_language item is missing or elsewhere
            if "host_languages" in json_listing:
                ehl = json_listing["host_languages"]
                if len(ehl) > 254:
                    listing.extra_host_languages = ehl[:254]
                else:
                    listing.extra_host_languages = ehl
            else:
                listing.extra_host_languages = None
            if "name" in json_listing:
                lname = json_listing["name"]
                if len(lname) > 254:
                    listing.name = lname[:254]
                else:
                    listing.name = lname
            else:
                listing.name = None
            if "room_and_property_type" in json_listing:
                pt = json_listing["room_and_property_type"]
                if len(pt) > 254:
                    listing.property_type = pt[:254]
                else:
                    listing.property_type = pt
            if "is_superhost" in json_listing:
                listing.is_superhost = json_listing["is_superhost"]
            if "min_nights" in json_listing:
                listing.minstay = json_listing["min_nights"]
            if "max_nights" in json_listing:
                listing.max_nights = json_listing["max_nights"]
            if "avg_rating" in json_listing:
                listing.avg_rating = json_listing["avg_rating"]
            if "picture_urls" in json_listing:
                listing.pictures = json_listing["picture_urls"]
            else:
                listing.pictures = None
            if "bathroom_label" in json_listing:
                listing.bathroom = json_listing["bathroom_label"]

            if "structured_stay_display_price" in json_pricing:
                structured_price = json_pricing['structured_stay_display_price']['primary_line']['price']
                listing.price = structured_price.split('$')[1].split()[0]
                listing.currency = structured_price.split()[1]

            # pricing
            # json_pricing = json["pricing_quote"]
            # listing.price = json_pricing["rate"]["amount"] if "rate" in json_pricing else None
            # listing.currency = json_pricing["rate"]["currency"] if "rate" in json_pricing else None
            # listing.rate_type = json_pricing["rate_type"] if "rate_type" in json_pricing else None

            return listing
        except:
            logger.exception(
                "Error in survey.listing_from_search_page_json: returning None")
            sys.exit(-1)
            return None

    def log_progress(self, room_type, neighborhood_id,
                     guests, section_offset, has_rooms):
        """ Add an entry to the survey_progress_log table to record the fact
        that a page has been visited.
        This does not apply to search by bounding box, but does apply to both
        neighborhood and zipcode searches, which is why it is in ABSurvey.
        """
        try:
            page_info = (self.survey_id, room_type, neighborhood_id,
                         guests, section_offset, has_rooms)
            logger.debug("Search page: " + str(page_info))
            sql = """
            insert into survey_progress_log
            (survey_id, room_type, neighborhood_id,
            guests, page_number, has_rooms)
            values (%s, %s, %s, %s, %s, %s)
            """
            conn = self.config.connect()
            cur = conn.cursor()
            cur.execute(sql, page_info)
            cur.close()
            conn.commit()
            logger.debug("Logging survey search page for neighborhood " +
                         str(neighborhood_id))
            return True
        except psycopg2.Error as pge:
            logger.error(pge.pgerror)
            cur.close()
            conn.rollback()
            return False
        except Exception:
            logger.error("Save survey search page failed")
            return False

    def fini(self):
        """
        Wrap up a survey: correcting status and survey_date
        """
        try:
            logger.info("Finishing survey %s, for %s",
                        self.survey_id, self.search_area_name)
            sql_update = """
            update survey
            set survey_date = (
            select min(last_modified)
            from room
            where room.survey_id = survey.survey_id
            ), status = 1
            where survey_id = %s
            """
            conn = self.config.connect()
            cur = conn.cursor()
            cur.execute(sql_update, (self.survey_id, ))
            cur.close()
            conn.commit()
            return True
        except:
            logger.exception("Survey fini failed")
            return False

    def page_has_been_retrieved(self, room_type, neighborhood_or_zipcode,
                                guests, page_number, search_by):
        """
        Used with neighborhood and zipcode logging (see method above).
        Returns 1 if the page has been retrieved previously and has rooms
        Returns 0 if the page has been retrieved previously and has no rooms
        Returns -1 if the page has not been retrieved previously
        """
        conn = self.config.connect()
        cur = conn.cursor()
        has_rooms = 0
        try:
            if search_by == self.config.SEARCH_BY_NEIGHBORHOOD:
                neighborhood = neighborhood_or_zipcode
                # TODO: Currently fails when there are no neighborhoods
                if neighborhood is None:
                    has_rooms = -1
                else:
                    params = (self.survey_id, room_type, neighborhood, guests,
                              page_number,)
                    logger.debug("Params: " + str(params))
                    sql = """
                    select spl.has_rooms
                    from survey_progress_log spl
                    join neighborhood nb
                    on spl.neighborhood_id = nb.neighborhood_id
                    where survey_id = %s
                    and room_type = %s
                    and nb.name = %s
                    and guests = %s
                    and page_number = %s"""
                    cur.execute(sql, params)
                    has_rooms = cur.fetchone()[0]
                    logger.debug("has_rooms = %s for neighborhood %s",
                                 str(has_rooms), neighborhood)
            else:  # SEARCH_BY_ZIPCODE
                zipcode = int(neighborhood_or_zipcode)
                params = (self.survey_id, room_type,
                          zipcode, guests, page_number,)
                logger.debug(params)
                sql = """
                    select spl.has_rooms
                    from survey_progress_log spl
                    where survey_id = %s
                    and room_type = %s
                    and neighborhood_id = %s
                    and guests = %s
                    and page_number = %s"""
                cur.execute(sql, params)
                has_rooms = cur.fetchone()[0]
                logger.debug("has_rooms = %s for zipcode %s",
                             str(has_rooms), str(zipcode))
        except Exception:
            has_rooms = -1
            logger.debug("Page has not been retrieved previously")
        finally:
            cur.close()
            return has_rooms


class ABSurveyByBoundingBox(ABSurvey):
    """
    Subclass of Survey that carries out a survey by a quadtree of bounding
    boxes: recursively searching rectangles.
    """

    def __init__(self, config, survey_id):
        super().__init__(config, survey_id)
        self.search_node_counter = 0
        self.logged_progress = self.get_logged_progress()
        self.bounding_box = self.get_bounding_box()

    def get_logged_progress(self):
        """
        Retrieve from the database the progress logged in previous attempts to
        carry out this survey, to pick up where we left off.
        Returns None if there is no progress logged.
        """
        try:
            sql = """
            select room_type, quadtree_node, median_node
            from survey_progress_log_bb
            where survey_id = %s
            """
            conn = self.config.connect()
            cur = conn.cursor()
            cur.execute(sql, (self.survey_id,))
            row = cur.fetchone()
            cur.close()
            conn.commit()
            if row is None:
                logger.debug("No progress logged for survey %s",
                             self.survey_id)
                self.logged_progress = None
            else:
                logged_progress = {}
                logged_progress["room_type"] = row[0]
                logged_progress["quadtree"] = eval(row[1])
                logged_progress["median"] = eval(row[2])
                logger.info("Resuming survey - retrieved logged progress")
                logger.info("\troom_type=%s", logged_progress["room_type"])
                logger.info("\tquadtree node=%s", logged_progress["quadtree"])
                logger.info("\tmedian node=%s", logged_progress["median"])
                return logged_progress
        except Exception:
            logger.exception(
                "Exception in get_progress: setting logged progress to None")
            return None

    def get_bounding_box(self):
        try:
            # Get the bounding box
            conn = self.config.connect()
            cur = conn.cursor()
            cur.execute("""
                        select bb_n_lat, bb_e_lng, bb_s_lat, bb_w_lng
                        from search_area sa join survey s
                        on sa.search_area_id = s.search_area_id
                        where s.survey_id = %s""", (self.survey_id,))
            # result comes back as a tuple. We want it mutable later, so
            # convert to a list [n_lat, e_lng, s_lat, w_lng]
            bounding_box = list(cur.fetchone())
            cur.close()
            # Validate the bounding box
            if None in bounding_box:
                logger.error("Invalid bounding box: contains 'None'")
                return None
            if bounding_box[0] <= bounding_box[2]:
                logger.error("Invalid bounding box: n_lat must be > s_lat")
                return None
            if bounding_box[1] <= bounding_box[3]:
                logger.error("Invalid bounding box: e_lng must be > w_lng")
                return None
            return bounding_box
        except Exception:
            logger.exception("Exception in set_bounding_box")
            self.bounding_box = None

    def search(self, flag):
        """
        Initialize bounding box search.
        A bounding box is a rectangle around a city, specified in the
        search_area table. The loop goes to quadrants of the bounding box
        rectangle and, if new listings are found, breaks that rectangle
        into four quadrants and tries again, recursively.
        The rectangles, including the bounding box, are represented by
        [n_lat, e_lng, s_lat, w_lng], because Airbnb uses the SW and NE
        corners of the box.
        """
        try:
            logger.info("=" * 70)
            logger.info("Survey {survey_id}, for {search_area_name}".format(
                survey_id=self.survey_id, search_area_name=self.search_area_name
            ))
            ABSurvey.update_survey_entry(
                self, self.config.SEARCH_BY_BOUNDING_BOX)
            logger.info("Searching by bounding box, max_zoom=%s",
                        self.config.SEARCH_MAX_RECTANGLE_ZOOM)
            # Initialize search parameters
            # quadtree_node holds the quadtree: each rectangle is
            # divided into 00 | 01 | 10 | 11, and the next level down adds
            # set starting point
            quadtree_node = []  # list of [0,0] etc coordinates
            median_node = []  # median lat, long to define optimal quadrants
            # set starting point for survey being resumed
            if self.logged_progress:
                logger.info("Restarting incomplete survey")
            if self.config.SEARCH_DO_LOOP_OVER_ROOM_TYPES:
                for room_type in self.room_types:
                    logger.info("-" * 70)
                    logger.info("Beginning of search for %s", room_type)
                    self.recurse_quadtree(
                        quadtree_node, median_node, room_type, flag)
            else:
                self.recurse_quadtree(quadtree_node, median_node, None, flag)
            self.fini()
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception:
            logger.exception("Error")

    def recurse_quadtree(self, quadtree_node, median_node, room_type, flag):
        """
        Recursive function to search for listings inside a rectangle.
        The actual search calls are done in search_node, and
        this method (recurse_quadtree) prints output and sets up new
        rectangles, if necessary, for another round of searching.

        To match Airbnb's use of SW and NE corners, quadrants are divided
        like this:

                     [0, 1] (NW)   |   [0, 0] (NE)
                     -----------------------------
                     [1, 1] (SW)   |   [1, 0] (SE)

        The quadrants are searched in the order [0,0], [0,1], [1,0], [1,1]
        """
        try:
            zoomable = True
            if self.is_subtree_previously_completed(quadtree_node, room_type):
                logger.info(
                    "Resuming survey: subtree previously completed: %s", quadtree_node)
                # This node is part of a tree that has already been searched
                # completely in a previous attempt to run this survey.
                # Go immediately to the next quadrant at the current level,
                # or (if this is a [1, 1] node) go back up the tree one level.
                # For example: if quadtree_node is [0,0] and the logged
                # progress is [1,0] then the subtree for [0,0] is completed. If
                # progress is [0,0][0,1] then the subtree is not completed.
                # TODO: use the same technique as the loop, below
                if not quadtree_node:
                    return
                if quadtree_node[-1] == [0, 0]:
                    quadtree_node[-1] = [0, 1]
                elif quadtree_node[-1] == [0, 1]:
                    quadtree_node[-1] = [1, 0]
                elif quadtree_node[-1] == [1, 0]:
                    quadtree_node[-1] = [1, 1]
                elif quadtree_node[-1] == [1, 1]:
                    del quadtree_node[-1]
                return

            # The subtree for this node has not been searched completely, so we
            # will continue to explore the tree. But does the current node need
            # to be searched? Only if it is at least as far down the tree as
            # the logged progress.
            # TODO Currently the most recent quadrant is searched again: this
            # is not a big problem.
            searchable_node = (
                self.logged_progress is None
                or len(quadtree_node) >= len(self.logged_progress["quadtree"]))
            if searchable_node:
                # The logged_progress can be set to None, as the survey is now
                # resumed. This should be done only once, but it is repeated.
                # Still, it is cheap.
                self.logged_progress = None
                (zoomable, median_leaf) = self.search_node(
                    quadtree_node, median_node, room_type, flag)
            else:
                median_leaf = self.logged_progress["median"][-1]
                logger.info(
                    "Resuming survey: node previously searched: %s", quadtree_node)

            # Recurse through the tree
            if zoomable:
                # and len(self.logged_progress["quadtree"]) >= len(quadtree_node)):
                # append a node to the quadtree for a new level
                quadtree_node.append([0, 0])
                median_node.append(median_leaf)
                for int_leaf in range(4):
                    # Loop over [0,0], [0,1], [1,0], [1,1]
                    quadtree_leaf = [int(i)
                                     for i in str(bin(int_leaf))[2:].zfill(2)]
                    quadtree_node[-1] = quadtree_leaf
                    self.recurse_quadtree(quadtree_node, median_node,
                                          room_type, flag)
                # the search of the quadtree below this node is complete:
                # remove the leaf element from the tree and return to go up a level
                if len(quadtree_node) > 0:
                    del quadtree_node[-1]
                if len(median_node) > 0:
                    del median_node[-1]
            logger.debug(
                "Returning from recurse_quadtree for %s", quadtree_node)
            if flag == self.config.FLAGS_PRINT:
                # for FLAGS_PRINT, fetch one page and print it
                sys.exit(0)
        except (SystemExit, KeyboardInterrupt):
            raise
        except TypeError as type_error:
            logger.exception("TypeError in recurse_quadtree")
            logger.error(type_error.args)
            raise
        except:
            logger.exception("Error in recurse_quadtree")
            raise

    def search_node(self, quadtree_node, median_node, room_type, flag):
        """
            rectangle is (n_lat, e_lng, s_lat, w_lng)
            returns number of *new* rooms and number of pages tested
        """
        try:
            logger.info("-" * 70)
            rectangle = self.get_rectangle_from_quadtree_node(
                quadtree_node, median_node)
            logger.info("Searching rectangle: zoom factor = %s, node = %s",
                        len(quadtree_node), str(quadtree_node))
            logger.debug("Rectangle: N={n:+.5f}, E={e:+.5f}, S={s:+.5f}, W={w:+.5f}"
                         .format(n=rectangle[0], e=rectangle[1],
                                 s=rectangle[2], w=rectangle[3]))
            new_rooms = 0
            # set zoomable to false if the search finishes without returning a
            # full complement of 20 pages, 18 listings per page
            zoomable = True

            # median_lists are collected from results on each page and used to
            # calculate the median values, which will be used to divide the
            # volume into optimal "quadrants".
            median_lists = {}
            median_lists["latitude"] = []
            median_lists["longitude"] = []
            # As of October 2018, Airbnb uses items_offset in the URL for each new page,
            # which is the offset in the number of listings, rather than the
            # number of pages. Thanks to domatka78 for identifying the change.
            items_offset = 0
            room_count = 0
            for section_offset in range(0, self.config.SEARCH_MAX_PAGES):
                self.search_node_counter += 1
                # section_offset is the zero-based counter used on the site
                # page number is convenient for logging, etc
                page_number = section_offset + 1
                items_offset += room_count
                room_count = 0

                if self.config.API_KEY:
                    # API (returns JSON)
                    # set up the parameters for the request
                    logger.debug("API key found: using API search at %s",
                                 self.config.URL_API_SEARCH_ROOT)
                    params = {}
                    params["_format"] = "for_explore_search_web"
                    params["_intents"] = "p1"
                    params["adults"] = str(0)
                    params["allow_override[]"] = ""
                    params["auto_ib"] = str(False)
                    params["children"] = str(0)
                    params["client_session_id"] = self.config.CLIENT_SESSION_ID
                    # params["currency"] = "CAD"
                    params["experiences_per_grid"] = str(20)
                    params["federated_search_session_id"] = "45de42ea-60d4-49a9-9335-9e52789cd306"
                    params["fetch_filters"] = str(True)
                    params["guests"] = str(0)
                    params["guidebooks_per_grid"] = str(20)
                    params["has_zero_guest_treatment"] = str(True)
                    params["infants"] = str(0)
                    params["is_guided_search"] = str(True)
                    params["is_new_cards_experiment"] = str(True)
                    params["is_standard_search"] = str(True)
                    params["items_offset"] = str(18)
                    params["items_per_grid"] = str(18)
                    # params["locale"] = "en-CA"
                    params["key"] = self.config.API_KEY
                    params["luxury_pre_launch"] = str(False)
                    params["metadata_only"] = str(False)
                    # params["query"] = "Lisbon Portugal"
                    params["query_understanding_enabled"] = str(True)
                    params["refinement_paths[]"] = "/homes"
                    if self.config.SEARCH_DO_LOOP_OVER_ROOM_TYPES:
                        params["room_types[]"] = room_type
                    params["search_type"] = "PAGINATION"
                    params["search_by_map"] = str(True)
                    params["section_offset"] = section_offset
                    params["selected_tab_id"] = "home_tab"
                    params["show_groupings"] = str(True)
                    params["supports_for_you_v3"] = str(True)
                    params["timezone_offset"] = "-240"
                    params["ne_lat"] = str(rectangle[0])
                    params["ne_lng"] = str(rectangle[1])
                    params["sw_lat"] = str(rectangle[2])
                    params["sw_lng"] = str(rectangle[3])
                    params["screen_size"] = "medium"
                    params["zoom"] = str(True)
                    # params["version"] = "1.4.8"
                    if items_offset > 0:
                        params["items_offset"] = str(items_offset)
                        # params["items_offset"]   = str(18*items_offset)
                        params["section_offset"] = str(8)
                    # make the http request

                    response = airbnb_ws.ws_request_with_repeats(
                        self.config, self.config.URL_API_SEARCH_ROOT, params)
                    # process the response
                    if response:
                        json_doc = json.loads(response.text)
                    else:
                        # If no response, maybe it's a network problem rather
                        # than a lack of data.To be conservative go to the next page
                        # rather than the next rectangle
                        logger.warning(
                            "No response received from request despite multiple attempts: %s",
                            params)
                        continue
                else:
                    # Web page (returns HTML)
                    logger.debug("No API key found in config file: using web search at %s",
                                 self.config.URL_API_SEARCH_ROOT)
                    logger.warning("These results are probably wrong")
                    logger.warning("See README for how to set an API key")
                    params = {}
                    params["source"] = "filter"
                    params["_format"] = "for_explore_search_web"
                    params["experiences_per_grid"] = str(20)
                    params["items_per_grid"] = str(18)
                    params["guidebooks_per_grid"] = str(20)
                    params["auto_ib"] = str(True)
                    params["fetch_filters"] = str(True)
                    params["has_zero_guest_treatment"] = str(True)
                    params["is_guided_search"] = str(True)
                    params["is_new_cards_experiment"] = str(True)
                    params["luxury_pre_launch"] = str(False)
                    params["query_understanding_enabled"] = str(True)
                    params["show_groupings"] = str(True)
                    params["supports_for_you_v3"] = str(True)
                    params["timezone_offset"] = "-240"
                    params["metadata_only"] = str(False)
                    params["is_standard_search"] = str(True)
                    params["refinement_paths[]"] = "/homes"
                    params["selected_tab_id"] = "home_tab"
                    params["allow_override[]"] = ""
                    params["ne_lat"] = str(rectangle[0])
                    params["ne_lng"] = str(rectangle[1])
                    params["sw_lat"] = str(rectangle[2])
                    params["sw_lng"] = str(rectangle[3])
                    params["search_by_map"] = str(True)
                    params["screen_size"] = "medium"
                    if section_offset > 0:
                        params["section_offset"] = str(section_offset)
                    # make the http request
                    response = airbnb_ws.ws_request_with_repeats(
                        self.config, self.config.URL_API_SEARCH_ROOT, params)
                    # process the response
                    if not response:
                        # If no response, maybe it's a network problem rather
                        # than a lack of data. To be conservative go to the next page
                        # rather than the next rectangle
                        logger.warning(
                            "No response received from request despite multiple attempts: %s",
                            params)
                        continue
                    soup = BeautifulSoup(response.content.decode("utf-8",
                                                                 "ignore"),
                                         "lxml")
                    html_file = open("test.html", mode="w", encoding="utf-8")
                    html_file.write(soup.prettify())
                    html_file.close()
                    # The returned page includes a script tag that encloses a
                    # comment. The comment in turn includes a complex json
                    # structure as a string, which has the data we need
                    spaspabundlejs_set = soup.find_all("script",
                                                       {"type": "application/json",
                                                        "data-hypernova-key": "spaspabundlejs"})
                    if spaspabundlejs_set:
                        logger.debug("Found spaspabundlejs tag")
                        comment = spaspabundlejs_set[0].contents[0]
                        # strip out the comment tags (everything outside the
                        # outermost curly braces)
                        json_doc = json.loads(
                            comment[comment.find("{"):comment.rfind("}")+1])
                        logger.debug("results-containing json found")
                    else:
                        logger.warning("json results-containing script node "
                                       "(spaspabundlejs) not found in the web page: "
                                       "go to next page")
                        return None
                # Now we have the json. It includes a list of 18 or fewer listings
                # if logger.isEnabledFor(logging.DEBUG):
                    # json_file = open(
                        # "json_listing_{}.json".format(self.search_node_counter),
                        # mode="w", encoding="utf-8")
                    # json_file.write(json.dumps(json_doc, indent=4, sort_keys=True))
                    # json_file.close()
                # Steal a function from StackOverflow which searches for items
                # with a given list of keys (in this case just one: "listing")
                # https://stackoverflow.com/questions/14048948/how-to-find-a-particular-json-value-by-key

                def search_json_keys(key, json_doc):
                    """ Return a list of the values for each occurrence of key
                    in json_doc, at all levels. In particular, "listings"
                    occurs more than once, and we need to get them all."""
                    found = []
                    if isinstance(json_doc, dict):
                        if key in json_doc.keys():
                            found.append(json_doc[key])
                        elif json_doc.keys():
                            for json_key in json_doc.keys():
                                result_list = search_json_keys(
                                    key, json_doc[json_key])
                                if result_list:
                                    found.extend(result_list)
                    elif isinstance(json_doc, list):
                        for item in json_doc:
                            result_list = search_json_keys(key, item)
                            if result_list:
                                found.extend(result_list)
                    return found

                # Get all items with tags "listings". Each json_listings is a
                # list, and each json_listing is a {listing, pricing_quote, verified}
                # dict for the listing in question
                # There may be multiple lists of listings
                json_listings_lists = search_json_keys("listings", json_doc)

                # json_doc = json_doc["explore_tabs"]
                # if json_doc: logger.debug("json: explore_tabs")
                # json_doc = json_doc["sections"]
                # if json_doc: logger.debug("json: sections")

                if json_listings_lists is not None:
                    room_count = 0
                    for json_listings in json_listings_lists:
                        if json_listings is None:
                            continue
                        for json_listing in json_listings:
                            room_id = int(json_listing["listing"]["id"])
                            if room_id is not None:
                                room_count += 1
                                listing = self.listing_from_search_page_json(
                                    json_listing, room_id)
                                if listing is None:
                                    continue
                                if listing.latitude is not None:
                                    median_lists["latitude"].append(
                                        listing.latitude)
                                if listing.longitude is not None:
                                    median_lists["longitude"].append(
                                        listing.longitude)
                                if listing.host_id is not None:
                                    listing.deleted = 0
                                    if flag == self.config.FLAGS_ADD:
                                        if listing.save(self.config.FLAGS_INSERT_NO_REPLACE):
                                            new_rooms += 1
                                    elif flag == self.config.FLAGS_PRINT:
                                        print(listing.room_type,
                                              listing.room_id)

                # Log page-level results
                logger.info("Page {page_number:02d} returned {room_count:02d} listings"
                            .format(page_number=page_number, room_count=room_count))
                if flag == self.config.FLAGS_PRINT:
                    # for FLAGS_PRINT, fetch one page and print it
                    sys.exit(0)
                if room_count < self.config.SEARCH_LISTINGS_ON_FULL_PAGE:
                    # If a full page of listings is not returned by Airbnb,
                    # this branch of the search is complete.
                    logger.info("Final page of listings for this search")
                    zoomable = False
                    break
            # Log node-level results
            if self.config.SEARCH_DO_LOOP_OVER_ROOM_TYPES:
                logger.info("Results: %s pages, %s new %s listings.",
                            page_number, new_rooms, room_type)
            else:
                logger.info("Results: %s pages, %s new rooms",
                            page_number, new_rooms)

            # Median-based partitioning not currently in use: may use later
            if len(median_node) == 0:
                median_leaf = "[]"
            else:
                median_leaf = median_node[-1]
            # calculate medians
            if room_count > 0:
                median_lat = round(sorted(median_lists["latitude"])
                                   [int(len(median_lists["latitude"])/2)], 5
                                   )
                median_lng = round(sorted(median_lists["longitude"])
                                   [int(len(median_lists["longitude"])/2)], 5
                                   )
                median_leaf = [median_lat, median_lng]
            else:
                # values not needed, but we need to fill in an item anyway
                median_leaf = [0, 0]
            # log progress
            self.log_progress(room_type, quadtree_node, median_node)
            return (zoomable, median_leaf)
        except UnicodeEncodeError:
            logger.error("UnicodeEncodeError: set PYTHONIOENCODING=utf-8")
            # if sys.version_info >= (3,):
            #    logger.info(s.encode('utf8').decode(sys.stdout.encoding))
            # else:
            #    logger.info(s.encode('utf8'))
            # unhandled at the moment
        except Exception:
            logger.exception("Exception in get_search_page_info_rectangle")
            raise

    def get_rectangle_from_quadtree_node(self, quadtree_node, median_node):
        try:
            rectangle = self.bounding_box[0:4]
            for node, medians in zip(quadtree_node, median_node):
                logger.debug("Quadtrees: %s", node)
                logger.debug("Medians: %s", medians)
                [n_lat, e_lng, s_lat, w_lng] = rectangle
                blur = abs(n_lat - s_lat) * \
                    self.config.SEARCH_RECTANGLE_EDGE_BLUR
                # find the mindpoints of the rectangle
                mid_lat = (n_lat + s_lat)/2.0
                mid_lng = (e_lng + w_lng)/2.0
                # mid_lat = medians[0]
                # mid_lng = medians[1]
                # overlap quadrants to ensure coverage at high zoom levels
                # Airbnb max zoom (18) is about 0.004 on a side.
                rectangle = []
                if node == [0, 0]:  # NE
                    rectangle = [round(n_lat + blur, 5),
                                 round(e_lng + blur, 5),
                                 round(mid_lat - blur, 5),
                                 round(mid_lng - blur, 5),]
                elif node == [0, 1]:  # NW
                    rectangle = [round(n_lat + blur, 5),
                                 round(mid_lng + blur, 5),
                                 round(mid_lat - blur, 5),
                                 round(w_lng - blur, 5),]
                elif node == [1, 0]:  # SE
                    rectangle = [round(mid_lat + blur, 5),
                                 round(e_lng + blur, 5),
                                 round(s_lat - blur, 5),
                                 round(mid_lng - blur, 5),]
                elif node == [1, 1]:  # SW
                    rectangle = [round(mid_lat + blur, 5),
                                 round(mid_lng + blur, 5),
                                 round(s_lat - blur, 5),
                                 round(w_lng - blur, 5),]
            logger.info("Rectangle calculated: %s", rectangle)
            return rectangle
        except:
            logger.exception("Exception in get_rectangle_from_quadtree_node")
            return None

    def is_subtree_previously_completed(self, quadtree_node, room_type):
        """
        Return True if the child subtree of this node was completed
        in a previous attempt at this survey.
        """
        subtree_previously_completed = False
        if self.logged_progress:
            # Compare the current node to the logged progress node by
            # converting into strings, then comparing the integer value.
            logger.debug("room_type=%s, self.logged_progress['room_type']=%s",
                         room_type, self.logged_progress["room_type"])
            if self.config.SEARCH_DO_LOOP_OVER_ROOM_TYPES == 1:
                if (self.room_types.index(room_type)
                        < self.room_types.index(self.logged_progress["room_type"])):
                    subtree_previously_completed = True
                    return subtree_previously_completed
                if (self.room_types.index(room_type)
                        > self.room_types.index(self.logged_progress["room_type"])):
                    subtree_previously_completed = False
                    return subtree_previously_completed
            common_length = min(len(quadtree_node),
                                len(self.logged_progress["quadtree"]))
            s_this_quadrant = ''.join(str(quadtree_node[i][j])
                                      for j in range(0, 2)
                                      for i in range(0, common_length))
            s_logged_progress = ''.join(
                str(self.logged_progress["quadtree"][i][j])
                for j in range(0, 2)
                for i in range(0, common_length))
            if (s_this_quadrant != ""
                    and int(s_this_quadrant) < int(s_logged_progress)):
                subtree_previously_completed = True
        return subtree_previously_completed

    def log_progress(self, room_type, quadtree_node, median_node):
        try:
            # This upsert statement requires PostgreSQL 9.5
            # Convert the quadrant to a string with repr() before storing it
            sql = """
            insert into survey_progress_log_bb
            (survey_id, room_type, quadtree_node, median_node)
            values (%s, %s, %s, %s)
            on conflict ON CONSTRAINT survey_progress_log_bb_pkey
            do update
                set room_type = %s, quadtree_node = %s, median_node = %s
                , last_modified = now()
            where survey_progress_log_bb.survey_id = %s
            """
            conn = self.config.connect()
            cur = conn.cursor()
            cur.execute(sql, (self.survey_id,
                              room_type, repr(quadtree_node), repr(
                                  median_node),
                              room_type, repr(quadtree_node), repr(
                                  median_node),
                              self.survey_id))
            cur.close()
            conn.commit()
            logger.debug("Progress logged")
            return True
        except Exception as e:
            logger.warning("""Progress not logged: survey not affected, but
                    resume will not be available if survey is truncated.""")
            logger.exception(
                "Exception in log_progress: {e}".format(e=type(e)))
            conn.close()
            return False


def ABSurveyGlobal(ABSurvey):
    """
    Special search to randomly choose rooms from a range rather than to
    look at specific areas of the world.
    """

    def search(self, flag, search_by):
        logger.info("-" * 70)
        logger.info("Survey {survey_id}, for {search_area_name}".format(
            survey_id=self.survey_id, search_area_name=self.search_area_name
        ))
        ABSurvey.update_survey_entry(self, self.config.SEARCH_AREA_GLOBAL)
        room_count = 0
        while room_count < self.config.FILL_MAX_ROOM_COUNT:
            try:
                # get a random candidate room_id
                room_id = random.randint(0, self.config.ROOM_ID_UPPER_BOUND)
                listing = ABListing(self.config, room_id, self.survey_id)
                if room_id is None:
                    break
                else:
                    if listing.ws_get_room_info(self.config.FLAGS_ADD):
                        room_count += 1
            except AttributeError:
                logger.error(
                    "Attribute error: marking room as deleted.")
                listing.save_as_deleted()
            except Exception as ex:
                logger.exception("Error in search:" + str(type(ex)))
                raise
        self.fini()
