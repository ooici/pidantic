import os
from uuid import uuid4
from tempfile import mkstemp

import pidantic.pyon.pyon as pyon
from pidantic.pyon.persistence import PyonDB, PyonDataObject, PyonProcDataObject


class MockPyonContainer(object):

    proc_manager = {}
    _is_started = True

    def init(self):
        pass

    def spawn_process(self, name=None, module=None, cls=None, config=None,
            process_id=None):

        process_id = process_id or str(uuid4())

        self.proc_manager[process_id] = {
            'name': name,
            'module': module,
            'cls': cls,
            'config': config
        }
        return process_id

    def terminate_process(self, process_id):
        del(self.proc_manager[process_id])


class TestPyon(object):

    def setup(self):

        _, self.pyon_db_file = mkstemp()

        self.pyon_db_url = "sqlite:///%s" % self.pyon_db_file
        self.pyon_db = PyonDB(self.pyon_db_url)

        self.pyon_data_object = PyonDataObject()

        self.pyon_container = MockPyonContainer()

        self.pyon = pyon.Pyon(self.pyon_db, self.pyon_container,
                data_object=self.pyon_data_object)

    def teardown(self):
        os.remove(self.pyon_db_file)

    def test_download(self):

        testdir = os.path.dirname(__file__)
        testfile = os.path.join(testdir, "module_to_download.py")

        test_url = "file://%s" % testfile

        got_file = self.pyon.download_module(test_url)

        with open(got_file) as gfile:
            with open(testfile) as tfile:
                assert gfile.read() == tfile.read()

    def test_load_module(self):

        testdir = os.path.dirname(__file__)
        testfile = os.path.join(testdir, "module_to_download.py")

        module_name = self.pyon.load_module(testfile, "modname")

        mod = __import__(module_name)

        tp = mod.TestProcess()
        assert tp.gettrue()

    def test_run(self):
        testdir = os.path.dirname(__file__)
        testfile = os.path.join(testdir, "module_to_download.py")
        test_url = "file://%s" % testfile
        directory = 'fake'

        module = 'ion.my.real.module'
        module_uri = test_url
        cls = 'TestProcess'
        config_yaml = '{"some": "config"}'
        config = {"some": "config"}
        name = "myprocname"

        process = self.pyon.create_process_db(directory=directory,
                module=module, module_uri=module_uri, cls=cls,
                config=config_yaml, pyon_name=name)
        pyon_id = self.pyon.run_process(process)

        pyon_proc = self.pyon_container.proc_manager[pyon_id]

        assert self.pyon.getState()

        assert pyon_proc['cls'] == cls
        assert pyon_proc['module'] != module
        assert pyon_proc['module'].endswith(module.replace(".", "_"))
        assert pyon_proc['config'] == config

        self.pyon.terminate_process(name)
        self.pyon.remove_process(name)


