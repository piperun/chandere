# Copyright (C) 2017 Jakob Kreuze, All Rights Reserved.
#
# This file is part of Chandere.
#
# Chandere is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Chandere is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with Chandere. If not, see <http://www.gnu.org/licenses/>.

"""[Document me!]"""


class ChandereError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


def handle_anomalous_http_status(code: int, url=None):
    if code != 200:
        error = "Encountered HTTP/1.1 {}".format(code)
        if url is not None:
            error += " while fetching '{}'.".format(url)
        raise ChandereException(error)
