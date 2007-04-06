"""
Web interface to view and analyze shakespeare texts.
"""
import os

import paste.request
import genshi
import genshi.template

import shakespeare
import shakespeare.index
import shakespeare.format
import shakespeare.concordance
import shakespeare.dm

# import this after dm so that db connection is set
import annotater.store
import annotater.marginalia


cfg = shakespeare.conf()
template_path = cfg.get('web', 'template_dir')
template_loader = genshi.template.TemplateLoader([template_path],
        auto_reload=True)

class ShakespeareWebInterface(object):

    def response(self, result):
        status = '200 OK'
        headers = [('Content-type','text/html')]
        self.start_response(status, headers)
        return [result]

    def __call__(self, environ, start_response):
        self.path = environ['PATH_INFO']
        self.start_response = start_response
        self.queryinfo = paste.request.parse_formvars(environ)
        if self.path == '/':
            return self.index()
        elif self.path.startswith('/guide'):
            return self.guide()
        elif self.path.startswith('/view'):
            name = self.queryinfo.get('name', '')
            format = self.queryinfo.get('format', 'plain')
            return self.view(name, format)
        elif self.path.startswith('/concordance/word'): # order matters
            word = self.queryinfo.get('word', None)
            return self.concordance_word(word)
        elif self.path.startswith('/concordance'):
            return self.concordance_index()
        elif self.path.startswith('/annotation'):
            store = annotater.store.AnnotaterStore()
            return store(environ, start_response)
        elif self.path.startswith('/marginalia'):
            prefix = cfg.get('annotater', 'marginalia_prefix')
            media_app = annotater.marginalia.MarginaliaMedia(prefix)
            return media_app(environ, start_response)
        else:
            # change to 404 or similar
            return self.response('Error')

    def index(self):
        try:
            index = shakespeare.index.all
            tmpl = template_loader.load('index.html')
            result = tmpl.generate(works_index=index).render()
        except Exception, inst:
            result = '<p><strong>There was an error: ' +  str(inst) + '</strong></p>'
        return self.response(result)

    def guide(self):
        template = template_loader.load('guide.html')
        result = template.generate().render()
        return self.response(result)

    def view(self, name, format='plain'):
        import shakespeare.dm
        namelist = name.split()
        numtexts = len(namelist)
        textlist = [shakespeare.dm.Material.byName(tname) for tname in namelist]
        # special case (only return the first text)
        if format == 'raw':
            tpath = textlist[0].get_cache_path('plain')
            result = file(tpath).read()
            status = '200 OK'
            headers = [('Content-type','text/plain')]
            self.start_response(status, headers)
            return [result]
        texts = []
        for item in textlist:
            tpath = item.get_cache_path('plain')
            tfileobj = file(tpath)
            ttext = shakespeare.format.format_text(tfileobj, format)
            thtml = genshi.XML(ttext)
            texts.append(thtml)
        # would have assumed this would be 100.0/numtexts but for some reason
        # you need to allow more room (maybe because of the scrollbars?)
        # result is not consistent across browsers ...
        frame_width = 100.0/numtexts - 4.0
        if format == 'annotate':
            template = template_loader.load('view_annotate.html')
            prefix = cfg.get('annotater', 'marginalia_prefix')
            ## TODO: remove hardcoded application fqdn
            marginalia_media = annotater.marginalia.get_media_header(prefix,
                    'http://localhost:8080/')
            marginalia_media = genshi.HTML(marginalia_media)
            result = template.generate(
                    frame_width=frame_width,
                    texts=texts, 
                    marginalia_media=marginalia_media,
                    )
        else:
            template = template_loader.load('view.html')
            result = template.generate(frame_width=frame_width, texts=texts)
        # set to not strip whitespace as o/w whitespace in pre tag gets removed
        return self.response(result.render('html', strip_whitespace=False))

    def concordance_index(self):
        stats = shakespeare.concordance.Statistics()
        words = stats.keys()
        template = template_loader.load('concordance.html')
        result = template.generate(words=words)
        return self.response(result.render())

    def concordance_word(self, word=None):
        # TODO: sort by work etc
        import shakespeare.textutils
        refs = []
        cc = shakespeare.concordance.Concordance()
        if word is not None:
            refs = list(cc.get(word))
        newrefs = []
        for ref in refs:
            # we use the 'plain' format when building the concordance
            tpath = ref.text.get_cache_path('plain')
            ff = file(tpath)
            snippet = shakespeare.textutils.get_snippet(ff, ref.char_index)
            ref.snippet = snippet
        template = template_loader.load('concordance_by_word.html')
        result = template.generate(word=word, refs=refs) 
        return self.response(result.render())

