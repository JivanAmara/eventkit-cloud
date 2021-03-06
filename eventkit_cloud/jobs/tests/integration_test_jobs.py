# -*- coding: utf-8 -*-
import json
import logging
import os
import requests
import shutil
import sqlite3
from time import sleep

from ...tasks.models import ExportTask, ExportProviderTask
from ...tasks.export_tasks import TaskStates
from ..models import ExportProvider, ExportProviderType, Job
from ...utils.geopackage import check_content_exists, check_zoom_levels

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger(__name__)


class TestJob(TestCase):
    """
    Test cases for Job model
    """

    def setUp(self):
        username = 'admin'
        password = '@dm1n'
        self.base_url = os.getenv('BASE_URL', 'http://{0}'.format(getattr(settings,"SITE_NAME", "cloud.eventkit.dev")))
        self.login_url = self.base_url + '/auth/'
        self.create_export_url = self.base_url + '/exports/create'
        self.jobs_url = self.base_url + reverse('api:jobs-list')
        self.runs_url = self.base_url + reverse('api:runs-list')
        self.download_dir = os.path.join(os.getenv('EXPORT_STAGING_ROOT', '.'), "test")
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir, mode=0660)
        self.client = requests.session()
        self.client.get(self.login_url)
        self.csrftoken = self.client.cookies['csrftoken']

        login_data = dict(username=username, password=password, csrfmiddlewaretoken=self.csrftoken, next='/')
        self.client.post(self.login_url, data=login_data, headers=dict(Referer=self.login_url),
                         auth=(username, password))
        self.client.get(self.base_url)
        self.client.get(self.create_export_url)
        self.csrftoken = self.client.cookies['csrftoken']
        self.selection = {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "MultiPolygon",
                                                                                              "coordinates": [
                                                                                                  [[[127.01, 37.01],
                                                                                                    [127.03, 37.02],
                                                                                                    [127.03, 37.03],
                                                                                                    [127.02, 37.03],
                                                                                                    [127.01, 37.01]]],
                                                                                                  [[[127.03, 37.03],
                                                                                                    [127.04, 37.03],
                                                                                                    [127.05, 37.05],
                                                                                                    [127.03, 37.04],
                                                                                                    [127.03, 37.03]]]
                                                                                              ]
                                                                                              }}]}
    def tearDown(self):
        if os.path.exists(self.download_dir):
            shutil.rmtree(self.download_dir)

    def test_osm_geopackage(self):
        """
        This test is to ensure that an OSM file by itself only exporting GeoPackage returns data.
        :return:
        """
        job_data = {"csrfmiddlewaretoken": self.csrftoken, "name": "TestGPKG", "description": "Test Description",
                    "event": "TestProject", "selection": self.selection, "tags": [],
                    "provider_tasks": [{"provider": "OpenStreetMap Data (Generic)", "formats": ["gpkg"]}]}
        self.assertTrue(self.run_job(job_data))

    def test_cancel_job(self):

        #update provider to ensure it runs long enough to cancel...
        export_provider = ExportProvider.objects.get(slug="eventkit-integration-test-wms")
        original_level_to = export_provider.level_to
        export_provider.level_to = 19
        export_provider.save()

        job_data = {"csrfmiddlewaretoken": self.csrftoken, "name": "eventkit-integration-test-wms", "description": "Test Description",
                    "event": "TestProject", "selection": self.selection, "tags": [],
                    "provider_tasks": [{"provider": "eventkit-integration-test-wms", "formats": ["gpkg"]}]}

        job_json = self.run_job(job_data, wait_for_run=False)

        run_json = self.wait_for_task_pickup(job_uid=job_json.get('uid'))

        export_provider_task = ExportProviderTask.objects.get(uid=run_json.get('provider_tasks')[0].get('uid'))

        self.client.get(self.create_export_url) 
        self.csrftoken = self.client.cookies['csrftoken']

        provider_url = self.base_url + reverse('api:provider_tasks-list') + '/{0}'.format(export_provider_task.uid)
        response = self.client.patch(provider_url,
                                    headers={'X-CSRFToken': self.csrftoken,
                                             'referer': self.create_export_url})
        self.assertEqual(200, response.status_code)
        self.assertEqual({'success': True}, json.loads(response.content))
        self.orm_job = Job.objects.get(uid=job_json.get('uid'))
        self.orm_run = self.orm_job.runs.last()

        pt = ExportProviderTask.objects.get(uid=export_provider_task.uid)

        self.assertTrue(all(_.status == TaskStates.CANCELED.value for _ in pt.tasks.all()))
        self.assertEqual(pt.status, TaskStates.CANCELED.value)

        self.wait_for_run(self.orm_job.uid)
        self.orm_run = self.orm_job.runs.last()
        self.assertEqual(self.orm_run.status, TaskStates.CANCELED.value)

        # update provider to original setting.
        export_provider = ExportProvider.objects.get(slug="eventkit-integration-test-wms")
        export_provider.level_to = original_level_to
        export_provider.save()

        delete_response = self.client.delete(self.jobs_url + '/' + job_json.get('uid'),
                                             headers={'X-CSRFToken': self.csrftoken, 'Referer': self.create_export_url})
        self.assertTrue(delete_response)

    def test_osm_geopackage_thematic(self):
        """
        This test is to ensure that an OSM job will export a thematic GeoPackage.
        :returns:
        """
        job_data = {"csrfmiddlewaretoken": self.csrftoken, "name": "TestThematicGPKG",
                    "description": "Test Description",
                    "event": "TestProject", "selection": self.selection, "tags": [],
                    "provider_tasks": [{"provider": "OpenStreetMap Data (Themes)", "formats": ["gpkg"]}]}
        self.assertTrue(self.run_job(job_data))

    def test_osm_sqlite(self):
        """
        This test is to ensure that an OSM will export a sqlite file.
        :return:
        """
        job_data = {"csrfmiddlewaretoken": self.csrftoken, "name": "TestSQLITE", "description": "Test Description",
                    "event": "TestProject", "selection": self.selection, "tags": [],
                    "provider_tasks": [{"provider": "OpenStreetMap Data (Generic)", "formats": ["sqlite"]}]}
        self.assertTrue(self.run_job(job_data))

    def test_osm_sqlite_thematic(self):
        """
        This test is to ensure that an OSM job will export a thematic sqlite file.
        :returns:
        """
        job_data = {"csrfmiddlewaretoken": self.csrftoken, "name": "TestThematicSQLITE",
                    "description": "Test Description",
                    "event": "TestProject", "selection": self.selection, "tags": [],
                    "provider_tasks": [{"provider": "OpenStreetMap Data (Themes)", "formats": ["sqlite"]}]}
        self.assertTrue(self.run_job(job_data))

    def test_osm_shp(self):
        """
        This test is to ensure that an OSM job will export a shp.
        :returns:
        """
        job_data = {"csrfmiddlewaretoken": self.csrftoken, "name": "TestSHP", "description": "Test Description",
                    "event": "TestProject", "selection": self.selection, "tags": [],
                    "provider_tasks": [{"provider": "OpenStreetMap Data (Generic)", "formats": ["shp"]}]}
        self.assertTrue(self.run_job(job_data))

    def test_osm_shp_thematic(self):
        """
        This test is to ensure that an OSM job will export a thematic shp.
        :returns:
        """
        job_data = {"csrfmiddlewaretoken": self.csrftoken, "name": "TestThematicSHP", "description": "Test Description",
                    "event": "TestProject", "selection": self.selection, "tags": [],
                    "provider_tasks": [{"provider": "OpenStreetMap Data (Themes)", "formats": ["shp"]}]}
        self.assertTrue(self.run_job(job_data))

    def test_osm_kml(self):
        """
        This test is to ensure that an OSM job will export a kml file.
        :returns:
        """
        job_data = {"csrfmiddlewaretoken": self.csrftoken, "name": "TestKML", "description": "Test Description",
                    "event": "TestProject", "selection": self.selection, "tags": [],
                    "provider_tasks": [{"provider": "OpenStreetMap Data (Generic)", "formats": ["kml"]}]}
        self.assertTrue(self.run_job(job_data))

    def test_osm_kml_thematic(self):
        """
        This test is to ensure that an OSM job will export a kml file.
        :returns:
        """
        job_data = {"csrfmiddlewaretoken": self.csrftoken, "name": "TestThematicKML", "description": "Test Description",
                    "event": "TestProject", "selection": self.selection, "tags": [],
                    "provider_tasks": [{"provider": "OpenStreetMap Data (Themes)", "formats": ["kml"]}]}
        self.assertTrue(self.run_job(job_data))

    def test_wms_gpkg(self):
        """
        This test is to ensure that an WMS job will export a gpkg file.
        :returns:
        """
        job_data = {"csrfmiddlewaretoken": self.csrftoken, "name": "TestGPKG-WMS", "description": "Test Description",
                    "event": "TestProject", "selection": self.selection, "tags": [],
                    "provider_tasks": [{"provider": "eventkit-integration-test-wms", "formats": ["gpkg"]}]}
        self.assertTrue(self.run_job(job_data))

    def test_wmts_gpkg(self):
        """
        This test is to ensure that an WMTS job will export a gpkg file.
        :returns:
        """
        job_data = {"csrfmiddlewaretoken": self.csrftoken, "name": "TestGPKG-WMTS", "description": "Test Description",
                    "event": "TestProject", "selection": self.selection, "tags": [],
                    "provider_tasks": [{"provider": "eventkit-integration-test-wmts", "formats": ["gpkg"]}]}
        self.assertTrue(self.run_job(job_data))

    def test_arcgis_gpkg(self):
        """
        This test is to ensure that an ArcGIS job will export a gpkg file.
        :returns:
        """
        job_data = {"csrfmiddlewaretoken": self.csrftoken, "name": "TestGPKG-Arc-Raster",
                    "description": "Test Description",
                    "event": "TestProject", "selection": self.selection, "tags": [],
                    "provider_tasks": [{"provider": "eventkit-integration-test-arc-raster", "formats": ["gpkg"]}]}
        self.assertTrue(self.run_job(job_data))

    def test_wfs_gpkg(self):
        """
        This test is to ensure that an WFS job will export a gpkg file.
        :returns:
        """
        job_data = {"csrfmiddlewaretoken": self.csrftoken, "name": "TestGPKG-WFS", "description": "Test Description",
                    "event": "TestProject", "selection": self.selection, "tags": [],
                    "provider_tasks": [{"provider": "eventkit-integration-test-wfs", "formats": ["gpkg"]}]}
        self.assertTrue(self.run_job(job_data))

    def test_wfs_shp(self):
        """
        This test is to ensure that an WFS job will export a shp file.
        :returns:
        """
        job_data = {"csrfmiddlewaretoken": self.csrftoken, "name": "TestSHP-WFS", "description": "Test Description",
                    "event": "TestProject", "selection": self.selection, "tags": [],
                    "provider_tasks": [{"provider": "eventkit-integration-test-wfs", "formats": ["shp"]}]}
        self.assertTrue(self.run_job(job_data))

    def test_wfs_sqlite(self):
        """
        This test is to ensure that an WFS job will export a sqlite file.
        :returns:
        """
        job_data = {"csrfmiddlewaretoken": self.csrftoken, "name": "TestSQLITE-WFS", "description": "Test Description",
                    "event": "TestProject", "selection": self.selection, "tags": [],
                    "provider_tasks": [{"provider": "eventkit-integration-test-wfs", "formats": ["sqlite"]}]}
        self.assertTrue(self.run_job(job_data))

    def test_wfs_kml(self):
        """
        This test is to ensure that an WFS job will export a gpkg file.
        :returns:
        """
        job_data = {"csrfmiddlewaretoken": self.csrftoken, "name": "TestKML-WFS", "description": "Test Description",
                    "event": "TestProject", "selection": self.selection, "tags": [],
                    "provider_tasks": [{"provider": "eventkit-integration-test-wfs", "formats": ["kml"]}]}
        self.assertTrue(self.run_job(job_data))

    def test_arcgis_feature_service(self):
        """
        This test is to ensure that an ArcGIS Feature Service job will export a gpkg file.
        :returns:
        """
        job_data = {"csrfmiddlewaretoken": self.csrftoken, "name": "TestGPKG-Arcfs", "description": "Test Description",
                    "event": "TestProject", "selection": self.selection, "tags": [],
                    "provider_tasks": [{"provider": "eventkit-integration-test-arc-fs", "formats": ["gpkg"]}]}
        self.assertTrue(self.run_job(job_data))

    def test_all(self):
        """
        This test ensures that if all formats and all providers are selected that the test will finish.
        :return:
        """
        job_data = {"csrfmiddlewaretoken": self.csrftoken, "name": "test", "description": "test",
                    "event": "test", "selection": self.selection,
                    "tags": [], "provider_tasks": [{"provider": "eventkit-integration-test-wms",
                                                    "formats": ["shp", "gpkg", "kml", "sqlite"]},
                                                   {"provider": "OpenStreetMap Data (Generic)",
                                                    "formats": ["shp", "gpkg", "kml", "sqlite"]},
                                                   {"provider": "OpenStreetMap Data (Themes)",
                                                    "formats": ["shp", "gpkg", "kml", "sqlite"]},
                                                   {"provider": "eventkit-integration-test-wmts",
                                                    "formats": ["shp", "gpkg", "kml", "sqlite"]},
                                                   {"provider": "eventkit-integration-test-arc-raster",
                                                    "formats": ["shp", "gpkg", "kml", "sqlite"]},
                                                   {"provider": "eventkit-integration-test-wfs",
                                                    "formats": ["shp", "gpkg", "kml", "sqlite"]},
                                                   {"provider": "eventkit-integration-test-arc-fs",
                                                    "formats": ["shp", "gpkg", "kml", "sqlite"]}]}
        self.assertTrue(self.run_job(job_data))

    def test_rerun_all(self):
        """
        This test ensures that if all formats and all providers are selected
        that the test will finish then successfully rerun.
        :return:
        """
        job_data = {"csrfmiddlewaretoken": self.csrftoken, "name": "test", "description": "test",
                    "event": "test", "selection": self.selection,
                    "tags": [], "provider_tasks": [{"provider": "eventkit-integration-test-wms",
                                                    "formats": ["shp", "gpkg", "kml", "sqlite"]},
                                                   {"provider": "OpenStreetMap Data (Generic)",
                                                    "formats": ["shp", "gpkg", "kml", "sqlite"]},
                                                   {"provider": "OpenStreetMap Data (Themes)",
                                                    "formats": ["shp", "gpkg", "kml", "sqlite"]},
                                                   {"provider": "eventkit-integration-test-wmts",
                                                    "formats": ["shp", "gpkg", "kml", "sqlite"]},
                                                   {"provider": "eventkit-integration-test-arc-raster",
                                                    "formats": ["shp", "gpkg", "kml", "sqlite"]},
                                                   {"provider": "eventkit-integration-test-wfs",
                                                    "formats": ["shp", "gpkg", "kml", "sqlite"]},
                                                   {"provider": "eventkit-integration-test-arc-fs",
                                                    "formats": ["shp", "gpkg", "kml", "sqlite"]}]}
        response = self.client.post(self.jobs_url,
                                    json=job_data,
                                    headers={'X-CSRFToken': self.csrftoken,
                                             'Referer': self.create_export_url})
        self.assertEquals(response.status_code, 202)
        job = response.json()

        run = self.wait_for_run(job.get('uid'))
        self.assertTrue(run.get('status') == "COMPLETED")
        for provider_task in run.get('provider_tasks'):
            geopackage_url = self.get_gpkg_url(run, provider_task.get("name"))
            if not geopackage_url:
                continue
            geopackage_file = self.download_file(geopackage_url)
            self.assertTrue(os.path.isfile(geopackage_file))
            self.assertTrue(check_content_exists(geopackage_file))
            os.remove(geopackage_file)

        rerun_response = self.client.get('{0}/{1}/run'.format(self.jobs_url, job.get('uid')),
                                         headers={'X-CSRFToken': self.csrftoken,
                                                  'Referer': self.create_export_url})

        self.assertEquals(rerun_response.status_code, 202)
        rerun = self.wait_for_run(job.get('uid'))
        self.assertTrue(rerun.get('status') == "COMPLETED")
        for provider_task in rerun.get('provider_tasks'):
            geopackage_url = self.get_gpkg_url(rerun, provider_task.get("name"))
            if not geopackage_url:
                continue
            geopackage_file = self.download_file(geopackage_url)
            self.assertTrue(os.path.isfile(geopackage_file))
            self.assertTrue(check_content_exists(geopackage_file))
            os.remove(geopackage_file)

        delete_response = self.client.delete(self.jobs_url + '/' + job.get('uid'),
                                             headers={'X-CSRFToken': self.csrftoken, 'Referer': self.create_export_url})
        self.assertTrue(delete_response)

    def run_job(self, data, wait_for_run=True):
        # include zipfile
        data['include_zipfile'] = True

        response = self.client.post(self.jobs_url,
                                    json=data,
                                    headers={'X-CSRFToken': self.csrftoken,
                                             'Referer': self.create_export_url})
        self.assertEquals(response.status_code, 202)
        job = response.json()

        if not wait_for_run:
            return job

        run = self.wait_for_run(job.get('uid'))
        self.orm_job = orm_job = Job.objects.get(uid=job.get('uid'))
        self.orm_run = orm_run = orm_job.runs.last()
        date = timezone.now().strftime('%Y%m%d')
        test_zip_url = '%s%s%s/%s' % (
            self.base_url,
            settings.EXPORT_MEDIA_ROOT,
            run.get('uid'),
            '%s-%s-%s-%s.zip' % (
                orm_run.job.name,
                orm_run.job.event,
                'eventkit',
                date
            ))

        if not getattr(settings, "USE_S3", False):
            self.assertEquals(test_zip_url, run['zipfile_url'])

        assert '.zip' in orm_run.zipfile_url

        self.assertTrue(run.get('status') == "COMPLETED")
        for provider_task in run.get('provider_tasks'):
            geopackage_url = self.get_gpkg_url(run, provider_task.get("name"))
            if not geopackage_url:
                continue
            geopackage_file = self.download_file(geopackage_url)
            self.assertTrue(os.path.isfile(geopackage_file))
            self.assertTrue(check_content_exists(geopackage_file))
            self.assertTrue(check_zoom_levels(geopackage_file))
            os.remove(geopackage_file)
        delete_response = self.client.delete(self.jobs_url + '/' + job.get('uid'),
                                             headers={'X-CSRFToken': self.csrftoken, 'Referer': self.create_export_url})
        self.assertTrue(delete_response)
        for provider_task in run.get('provider_tasks'):
            geopackage_url = self.get_gpkg_url(run, provider_task.get("name"))
            if not geopackage_url:
                continue
            geopackage_file = self.download_file(geopackage_url)
            self.assertNotTrue(os.path.isfile(geopackage_file))
            if os.path.isfile(geopackage_file):
                os.remove(geopackage_file)
        return True

    def wait_for_task_pickup(self, job_uid):
        picked_up = False
        response = None
        while not picked_up:
            sleep(1)
            response = self.client.get(
                self.runs_url,
                params={"job_uid": job_uid},
                headers={'X-CSRFToken': self.csrftoken}).json()
            if response[0].get('provider_tasks'):
                picked_up = True
        return response[0]

    def wait_for_run(self, job_uid):
        finished = False
        response = None
        while not finished:
            sleep(1)
            response = self.client.get(
                self.runs_url,
                params={"job_uid": job_uid},
                headers={'X-CSRFToken': self.csrftoken
                         }).json()
            status = response[0].get('status')
            if status in [TaskStates.COMPLETED.value, TaskStates.INCOMPLETE.value, TaskStates.CANCELED.value]:
                finished = True
        return response[0]

    def download_file(self, url, download_dir=None):
        download_dir = download_dir or self.download_dir
        file_location = os.path.join(download_dir, os.path.basename(url))
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            with open(file_location, 'wb') as f:
                for chunk in r:
                    f.write(chunk)
            return file_location
        else:
            print("Failed to download GPKG, STATUS_CODE: {0}".format(r.status_code))
        return None

    @staticmethod
    def get_gpkg_url(run, provider_task_name):
        for provider_task in run.get("provider_tasks"):
            if provider_task.get('name') == provider_task_name:
                for task in provider_task.get('tasks'):
                    if task.get('name') == "Geopackage":
                        return task.get('result').get("url")
        return None


def get_providers_list():
    return [{
        "model": "jobs.exportprovider",
        "fields": {
            "created_at": "2016-10-06T17:44:54.837Z",
            "updated_at": "2016-10-06T17:44:54.837Z",
            "name": "eventkit-integration-test-wms",
            "slug": "eventkit-integration-test-wms",
            "url": "http://basemap.nationalmap.gov/arcgis/services/USGSImageryOnly/MapServer/WmsServer?",
            "layer": "0",
            "export_provider_type": ExportProviderType.objects.using('default').get(type_name='wms'),
            "level_from": 0,
            "level_to": 2,
            "config": ""
        }
    }, {
        "model": "jobs.exportprovider",
        "fields": {
            "created_at": "2016-10-06T17:45:46.213Z",
            "updated_at": "2016-10-06T17:45:46.213Z",
            "name": "eventkit-integration-test-wmts",
            "url": "https://basemap.nationalmap.gov/arcgis/rest/services/USGSShadedReliefOnly/MapServer/WMTS?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=USGSShadedReliefOnly&TILEMATRIXSET=WEBMERCATOR&TILEMATRIX=%(z)s&TILEROW=%(y)s&TILECOL=%(x)s&FORMAT=image%%2Fpng",
            "layer": "imagery",
            "export_provider_type": ExportProviderType.objects.using('default').get(type_name='wmts'),
            "level_from": 0,
            "level_to": 2,
            "config": "layers:\r\n - name: imagery\r\n   title: imagery\r\n   sources: [cache]\r\n\r\n"
                      "sources:\r\n"
                      "  imagery_wmts:\r\n"
                      "    type: tile\r\n"
                      "    grid: webmercator\r\n"
                      "    url: https://basemap.nationalmap.gov/arcgis/rest/services/USGSShadedReliefOnly/MapServer/WMTS?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=USGSShadedReliefOnly&TILEMATRIXSET=WEBMERCATOR&TILEMATRIX=%(z)s&TILEROW=%(y)s&TILECOL=%(x)s&FORMAT=image%%2Fpng\r\n\r\n"
                      "grids:\r\n  webmercator:\r\n    srs: EPSG:3857\r\n    tile_size: [256, 256]\r\n    origin: nw"
        }
    }, {
        "model": "jobs.exportprovider",
        "fields": {
            "created_at": "2016-10-06T19:17:28.770Z",
            "updated_at": "2016-10-06T19:17:28.770Z",
            "name": "eventkit-integration-test-arc-raster",
            "slug": "eventkit-integration-test-arc-raster",
            "url": "http://server.arcgisonline.com/arcgis/rest/services/ESRI_Imagery_World_2D/MapServer",
            "layer": "imagery",
            "export_provider_type": ExportProviderType.objects.using('default').get(type_name='arcgis-raster'),
            "level_from": 0,
            "level_to": 2,
            "config": "layer:\r\n  - name: imagery\r\n    title: imagery\r\n    sources: [cache]\r\n\r\n"
                      "sources:\r\n"
                      "  imagery_arcgis-raster:\r\n"
                      "    type: arcgis\r\n"
                      "    grid: webmercator\r\n"
                      "    req:\r\n"
                      "      url: http://server.arcgisonline.com/arcgis/rest/services/ESRI_Imagery_World_2D/MapServer\r\n"
                      "      layers: \r\n"
                      "        show: 0\r\n\r\n"
                      "grids:\r\n  webmercator:\r\n    srs: EPSG:3857\r\n    tile_size: [256, 256]\r\n    origin: nw"
        }
    }, {
        "model": "jobs.exportprovider",
        "fields": {
            "created_at": "2016-10-13T17:23:26.890Z",
            "updated_at": "2016-10-13T17:23:26.890Z",
            "name": "eventkit-integration-test-wfs",
            "slug": "eventkit-integration-test-wfs",
            "url": "http://geonode.state.gov/geoserver/wfs?SERVICE=WFS&VERSION=1.0.0&REQUEST=GetFeature&TYPENAME=geonode:EurasiaOceania_LSIB_Polygons_Simplified_2015&SRSNAME=EPSG:4326",
            "layer": "geonode:EurasiaOceania_LSIB_Polygons_Simplified_2015",
            "export_provider_type": ExportProviderType.objects.using('default').get(type_name='wfs'),
            "level_from": 0,
            "level_to": 2,
            "config": ""
        }
    }, {
        "model": "jobs.exportprovider",
        "fields": {
            "created_at": "2016-10-21T14:30:27.066Z",
            "updated_at": "2016-10-21T14:30:27.066Z",
            "name": "eventkit-integration-test-arc-fs",
            "slug": "eventkit-integration-test-arc-fs",
            "url": "http://services1.arcgis.com/0IrmI40n5ZYxTUrV/ArcGIS/rest/services/ONS_Boundaries_02/FeatureServer/0/query?where=objectid%3Dobjectid&outfields=*&f=json",
            "layer": "0",
            "export_provider_type": ExportProviderType.objects.using('default').get(type_name='arcgis-feature'),
            "level_from": 0,
            "level_to": 2,
            "config": ""
        }
    }]


def load_providers():
    export_providers = get_providers_list()
    for export_provider in export_providers:
        try:
            provider = ExportProvider.objects.using('default').create(
                name=export_provider.get('fields').get('name'),
                slug=export_provider.get('fields').get('slug'), url=export_provider.get('fields').get('url'),
                layer=export_provider.get('fields').get('layer'),
                export_provider_type=export_provider.get('fields').get('export_provider_type'),
                level_from=export_provider.get('fields').get('level_from'),
                level_to=export_provider.get('fields').get('level_to'),
                config=export_provider.get('fields').get('config'))
            provider.save(using='default')
        except IntegrityError:
            continue


def delete_providers():
    export_providers = get_providers_list()
    for export_provider in export_providers:
        provider = ExportProvider.objects.using('default').get(
            name=export_provider.get('fields').get('name')
        )
        provider.delete(using='default')
