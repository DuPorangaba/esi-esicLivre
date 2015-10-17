# coding: utf-8

from __future__ import unicode_literals  # unicode by default

import arrow
import sqlalchemy as sa
import sqlalchemy_utils as sa_utils
from sqlalchemy.orm.exc import NoResultFound

from extensions import db


pedido_attachments = sa.Table(
    'pedido_attachments', db.metadata,
    db.Column('pedido_id', db.Integer, db.ForeignKey('pedido.id')),
    db.Column('attachment_id', db.Integer, db.ForeignKey('attachment.id'))
)

pedido_keyword = sa.Table(
    'pedido_keyword', db.metadata,
    db.Column('pedido_id', db.Integer, db.ForeignKey('pedido.id')),
    db.Column('keyword_id', db.Integer, db.ForeignKey('keyword.id'))
)

pedido_author = sa.Table(
    'pedido_author', db.metadata,
    db.Column('pedido_id', db.Integer, db.ForeignKey('pedido.id')),
    db.Column('author_id', db.Integer, db.ForeignKey('author.id'))
)


class PedidosUpdate(db.Model):

    __tablename__ = 'pedidos_update'

    id = db.Column(db.Integer, primary_key=True)

    date = db.Column(sa_utils.ArrowType, index=True)


class PrePedido(db.Model):

    __tablename__ = 'pre_pedido'

    id = db.Column(db.Integer, primary_key=True)

    author_id = db.Column(db.Integer)

    orgao_name = db.Column(db.String(255))

    text = db.Column(sa.UnicodeText())

    keywords = db.Column(db.String(255))  # separated by commas

    state = db.Column(db.String(255))  # WAITING or PROCESSED

    created_at = db.Column(sa_utils.ArrowType)

    updated_at = db.Column(sa_utils.ArrowType)

    @property
    def as_dict(self):
        return {
            'id': self.id,
            'author_id': self.author_id,
            'orgao_name': self.orgao_name,
            'text': self.text,
            'keywords': [keyword for keyword in self.keywords.split(',')],
            'state': self.state
        }

    @classmethod
    def get_all_pending(self):
        return self.query.filter_by(state='WAITING')

    @property
    def orgao(self):
        return Orgao.query.filter_by(name=self.orgao_name).one()

    @property
    def author(self):
        return Author.query.filter_by(id=self.author_id).one()

    @property
    def all_keywords(self):
        return [
            Keyword.query.filter_by(name=k).one()
            for k in self.keywords.split(',')  # noqa
        ]

    def create_pedido(self, protocolo, deadline):

        pedido = Pedido()

        pedido.protocol = protocolo
        pedido.deadline = deadline

        pedido.orgao = self.orgao
        pedido.author = self.author
        pedido.keywords = self.all_keywords

        pedido.description = self.text
        # pedido.request_date = datetime.datetime.today()
        pedido.request_date = arrow.utcnow()

        db.session.add(pedido)
        db.session.commit()

        # self.updated_at = datetime.datetime.today()
        self.updated_at = arrow.utcnow()
        self.state = 'PROCESSED'

        db.session.add(self)
        db.session.commit()


class Pedido(db.Model):

    __tablename__ = 'pedido'

    id = db.Column(db.Integer, primary_key=True)

    protocol = db.Column(db.Integer, index=True, unique=True)

    interessado = db.Column(db.String(255))

    situation = db.Column(db.String(255), index=True)

    request_date = db.Column(sa_utils.ArrowType, index=True)

    contact_option = db.Column(db.String(255), nullable=True)

    description = db.Column(sa.UnicodeText())

    deadline = db.Column(sa_utils.ArrowType, index=True)

    orgao_name = db.Column(db.String(255))

    history = db.relationship("Message", backref="pedido")

    author = db.relationship(
        'Author', secondary=pedido_author, backref='pedidos', uselist=False
    )

    keywords = db.relationship(
        'Keyword', secondary=pedido_keyword, backref='pedidos'
    )

    attachments = db.relationship(
        'Attachment', secondary=pedido_attachments, backref='pedido'
    )

    @property
    def as_dict(self):
        return {
            'id': self.id,
            'protocol': self.protocol,
            'interessado': self.interessado,
            'situation': self.situation,
            'request_date': self.request_date,
            'contact_option': self.contact_option,
            'description': self.description,
            'deadline': self.deadline.isoformat() if self.deadline else '',
            'orgao_name': self.orgao_name,
            'history': [m.as_dict for m in self.history],
            'author': self.author.as_dict,
            'keywords': [kw.as_dict for kw in self.keywords],
            'attachments': [att.as_dict for att in self.attachments]
        }

    def add_keyword(self, keyword_name):
        try:
            keyword = (db.session.query(Keyword)
                       .filter_by(name=keyword_name).one())
        except NoResultFound:
            keyword = Keyword(name=keyword_name)
            db.session.add(keyword)
            db.session.commit()
        self.keywords.append(keyword)


class Orgao(db.Model):

    __tablename__ = 'orgao'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(255), nullable=False, unique=True)

    @property
    def as_dict(self):
        return {'id': self.id, 'name': self.name}


class Message(db.Model):

    __tablename__ = 'message'

    id = db.Column(db.Integer, primary_key=True)

    situation = db.Column(db.String(255))

    justification = db.Column(sa.UnicodeText())

    responsible = db.Column(db.String(255))

    date = db.Column(sa_utils.ArrowType, index=True)

    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'),
                          nullable=False)

    @property
    def as_dict(self):
        return {
            'id': self.id,
            'situation': self.situation,
            'justification': self.justification,
            'responsible': self.responsible,
            'date': self.date.isoformat(),
        }


class Author(db.Model):

    __tablename__ = 'author'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(255), nullable=False, unique=True)

    @property
    def as_dict(self):
        return {'id': self.id, 'name': self.name}


class Keyword(db.Model):

    __tablename__ = 'keyword'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(255), nullable=False, unique=True, index=True)

    @property
    def as_dict(self):
        return {'id': self.id, 'name': self.name}


class Attachment(db.Model):

    __tablename__ = 'attachment'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(255), nullable=False)

    created_at = db.Column(sa_utils.ArrowType)

    ia_url = db.Column(sa_utils.URLType)

    @property
    def as_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'ia_url': self.ia_url
        }
