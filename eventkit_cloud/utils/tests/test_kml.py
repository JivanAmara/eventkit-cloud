# -*- coding: utf-8 -*-
import logging
import os

from mock import Mock, patch

from django.test import TransactionTestCase

from ..kml import GPKGToKml

logger = logging.getLogger(__name__)


class TestGPKGToKml(TransactionTestCase):

    def setUp(self, ):
        self.path = os.path.dirname(os.path.realpath(__file__))

    @patch('eventkit_cloud.tasks.models.ExportTask')
    @patch('os.path.exists')
    @patch('subprocess.PIPE')
    @patch('subprocess.Popen')
    def test_convert(self, popen, pipe, exists, export_task):
        gpkg = '/path/to/query.gpkg'
        kmlfile = '/path/to/query.kml'
        cmd = "ogr2ogr -f 'KML' {0} {1}".format(kmlfile, gpkg)
        exists.return_value = True
        proc = Mock()
        popen.return_value = proc
        proc.communicate.return_value = (Mock(), Mock())
        proc.wait.return_value = 0
        # set zipped to False for testing
        s2k = GPKGToKml(gpkg=gpkg, kmlfile=kmlfile,
                          zipped=False, debug=False)
        exists.assert_called_once_with(gpkg)
        out = s2k.convert()
        export_task.assert_called_once()
        popen.assert_called_once_with(cmd, shell=True, executable='/bin/bash',
                                stdout=pipe, stderr=pipe)
        proc.communicate.assert_called_once()
        proc.wait.assert_called_once()
        self.assertEquals(out, kmlfile)

    @patch('eventkit_cloud.tasks.models.ExportTask')
    @patch('os.path.exists')
    @patch('os.remove')
    @patch('subprocess.PIPE')
    @patch('subprocess.Popen')
    def test_zip_kml_file(self, popen, pipe, remove, exists, export_task):
        gpkg = '/path/to/query.gpkg'
        kmlfile = '/path/to/query.kml'
        zipfile = '/path/to/query.kmz'
        zip_cmd = "zip -j {0} {1}".format(zipfile, kmlfile)
        exists.return_value = True
        proc = Mock()
        popen.return_value = proc
        proc.communicate.return_value = (Mock(), Mock())
        proc.wait.return_value = 0
        s2k = GPKGToKml(gpkg=gpkg, kmlfile=kmlfile,
                          zipped=False, debug=False)
        result = s2k._zip_kml_file()
        export_task.assert_called_once()
        exists.assert_called_once_with(gpkg)
        # test subprocess getting called with correct command
        popen.assert_called_once_with(zip_cmd, shell=True, executable='/bin/bash',
                                stdout=pipe, stderr=pipe)
        remove.assert_called_once_with(kmlfile)
        self.assertEquals(result, zipfile)
