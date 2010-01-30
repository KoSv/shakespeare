from shakespeare.tests import *

class TestAnnoController(TestController):
    @classmethod
    def setup_class(self):
        self.text = TestData.make_fixture()

    @classmethod
    def teardown_class(self):
        TestData.remove_fixtures()

    def test_index(self):
        res = self.app.get(url_for(controller='anno', action='index'))
        assert 'Choose a text to annotate' in res

    def test_annotate(self):
        res = self.app.get(url_for(controller='anno', action='annotate'))
        assert 'Annotate' in res
        assert 'No text to annotate' in res
    
    def test_choose_text(self):
        res = self.app.get(url_for(controller='anno', action='index'))
        form = res.forms[0]
        form['text'] = self.text.name
        res = form.submit()
        assert 'Annotate' in res 
        assert self.text.content.split()[0] in res, res
        assert '<pre' in res

    # run this last
    def test_z_annotation(self):
        res = self.app.get(url_for(controller='anno_store', action='annotation'))
        # no annotations so []
        assert [] in res, res

