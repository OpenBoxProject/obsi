#!/usr/bin/env python
#
# Copyright (c) 2015 Pavel Lazar pavel.lazar (at) gmail.com
#
# The Software is provided WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.
#####################################################################

import unittest
import configuration_builder.click_elements as elements
from configuration_builder.configuration_builder_exceptions import ClickElementConfigurationError


class TestNoArgsElement(unittest.TestCase):
    def setUp(self):
        self.expected = elements.SimpleIdle('simple_idle')
        self.parsed = elements.Element.from_dict(dict(name='simple_idle', type='SimpleIdle', config={}))

    def test_config_parsing(self):
        self.assertEqual(type(self.expected), type(self.parsed))
        self.assertEqual(self.expected.name, self.parsed.name)

    def test_click_config_string(self):
        expected_string = "simple_idle::SimpleIdle();"
        self.assertEqual(self.parsed.to_click_config(), expected_string)


class TestMandatoryOnlyElement(unittest.TestCase):
    def setUp(self):
        self.exp = elements.CheckAverageLength('chk', minlength="12")

    def test_config_parsing(self):
        config = dict(type='CheckAverageLength', name='chk', config=dict(minlength='12'))
        parsed = elements.Element.from_dict(config)
        self.assertEqual(type(parsed), type(self.exp))
        self.assertEqual(parsed.name, self.exp.name)
        self.assertEqual(parsed.minlength, self.exp.minlength)

    def test_no_mandatory_arg(self):
        config = dict(type='CheckAverageLength', name='chk')
        self.assertRaises(ClickElementConfigurationError, elements.Element.from_dict, config)

    def test_click_config_string(self):
        expected = 'chk::CheckAverageLength(12);'
        config = dict(type='CheckAverageLength', name='chk', config=dict(minlength='12'))
        parsed = elements.Element.from_dict(config)
        self.assertEqual(parsed.to_click_config(), expected)


class TestOptionalOnlyElement(unittest.TestCase):
    def test_config_parsing_with_mandatory_arg(self):
        expected = elements.TimedSink('ts', interval='12')
        config = dict(type='TimedSink', name='ts', config=dict(interval='12'))
        parsed = elements.Element.from_dict(config)
        self.assertEqual(type(parsed), type(expected))
        self.assertEqual(parsed.name, expected.name)
        self.assertEqual(parsed.interval, expected.interval)

    def test_config_parsing_without_mandatory_arg(self):
        expected = elements.TimedSink('ts', )
        config = dict(type='TimedSink', name='ts', config={})
        parsed = elements.Element.from_dict(config)
        self.assertEqual(type(parsed), type(expected))
        self.assertEqual(parsed.name, expected.name)

    def test_click_config_string_with_arg(self):
        config = dict(type='TimedSink', name='ts', config=dict(interval='12'))
        parsed = elements.Element.from_dict(config)
        expected = "ts::TimedSink(12);"
        self.assertEqual(parsed.to_click_config(), expected)

    def test_click_config_string_without_arg(self):
        config = dict(type='TimedSink', name='ts', config={})
        parsed = elements.Element.from_dict(config)
        expected = "ts::TimedSink();"
        self.assertEqual(parsed.to_click_config(), expected)


class TestKeywordOnlyElement(unittest.TestCase):
    def test_config_parsing_no_keywords(self):
        expected = elements.Discard('dis')
        config = dict(type='Discard', name='dis', config={})
        parsed = elements.Element.from_dict(config)
        self.assertEqual(type(parsed), type(expected))
        self.assertEqual(parsed.name, expected.name)

    def test_config_parsing_single_keyword(self):
        expected = elements.Discard('dis', burst='12')
        config = dict(type='Discard', name='dis', config=dict(burst='12'))
        parsed = elements.Element.from_dict(config)
        self.assertEqual(type(parsed), type(expected))
        self.assertEqual(parsed.name, expected.name)
        self.assertEqual(parsed.burst, expected.burst)

    def test_click_config_string_no_args(self):
        config = dict(type='Discard', name='dis')
        parsed = elements.Element.from_dict(config)
        expected = 'dis::Discard();'
        self.assertEqual(parsed.to_click_config(), expected)

    def test_click_config_string_with_args(self):
        config = dict(type='Discard', name='dis', config=dict(active='true', burst='12'))
        parsed = elements.Element.from_dict(config)
        expected = 'dis::Discard(ACTIVE true, BURST 12);'
        self.assertEqual(parsed.to_click_config(), expected)


class TestListOfArgumentsElement(unittest.TestCase):
    def test_config_parsing(self):
        expected = elements.Classifier('classifier', pattern=["pat1", "pat2"])
        config = dict(type="Classifier", name='classifier', config=dict(pattern=['pat1', 'pat2']))
        parsed = elements.Element.from_dict(config)
        self.assertEqual(type(parsed), type(expected))
        self.assertEqual(parsed.name, expected.name)
        self.assertEqual(parsed.pattern, expected.pattern)

    def test_click_config_string(self):
        config = dict(type="Classifier", name='classifier', config=dict(pattern=['pat1', 'pat2']))
        parsed = elements.Element.from_dict(config)
        expected = "classifier::Classifier(pat1, pat2);"
        self.assertEqual(parsed.to_click_config(), expected)


class TestOptionalAndKeywordsArgsElement(unittest.TestCase):
    def test_config_parsing_no_keyword(self):
        expected = elements.InfiniteSource('is', data='asdf', limit='12')
        config = dict(type='InfiniteSource', name='is', config=dict(data='asdf', limit='12'))
        parsed = elements.Element.from_dict(config)
        self.assertEqual(type(parsed), type(expected))
        self.assertEqual(parsed.name, expected.name)
        self.assertEqual(parsed.data, expected.data)
        self.assertEqual(parsed.limit, expected.limit)

    def test_config_parsing_no_optional(self):
        expected = elements.InfiniteSource('is', stop='true', length='12')
        config = dict(type='InfiniteSource', name='is', config=dict(stop='true', length='12'))
        parsed = elements.Element.from_dict(config)
        self.assertEqual(type(parsed), type(expected))
        self.assertEqual(parsed.name, expected.name)
        self.assertEqual(parsed.stop, expected.stop)
        self.assertEqual(parsed.length, expected.length)

    def test_config_parsing_both(self):
        expected = elements.InfiniteSource('is', data='asdf', stop='true', length='12')
        config = dict(type='InfiniteSource', name='is', config=dict(data='asdf', stop='true', length='12'))
        parsed = elements.Element.from_dict(config)
        self.assertEqual(type(parsed), type(expected))
        self.assertEqual(parsed.name, expected.name)
        self.assertEqual(parsed.data, expected.data)
        self.assertEqual(parsed.stop, expected.stop)
        self.assertEqual(parsed.length, expected.length)

    def test_click_config_string(self):
        config = dict(type='InfiniteSource', name='is', config=dict(data='asdf', stop='true', length='12'))
        parsed = elements.Element.from_dict(config)
        expected = "is::InfiniteSource(asdf, LENGTH 12, STOP true);"
        self.assertEqual(parsed.to_click_config(), expected)


class TestAllArgTypesElement(unittest.TestCase):
    def test_config_parsing(self):
        expected = elements.RandomSource("rs", length='12', limit='2', stop='true')
        config = dict(type='RandomSource', name='rs', config=dict(length='12', limit='2', stop='true'))
        parsed = elements.Element.from_dict(config)
        self.assertEqual(type(parsed), type(expected))
        self.assertEqual(parsed.name, expected.name)
        self.assertEqual(parsed.length, expected.length)
        self.assertEqual(parsed.limit, expected.limit)
        self.assertEqual(parsed.stop, expected.stop)

    def test_click_config_string(self):
        config = dict(type='RandomSource', name='rs', config=dict(length='12', limit='2', stop='true'))
        parsed = elements.Element.from_dict(config)
        expected = "rs::RandomSource(12, 2, STOP true);"
        self.assertEqual(parsed.to_click_config(), expected)
