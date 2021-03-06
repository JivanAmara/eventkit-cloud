import {ImportButton} from '../components/ImportButton';
import React from 'react';
import {expect} from 'chai';
import sinon from 'sinon';
import {mount, shallow} from 'enzyme';
import FileFileUpload from 'material-ui/svg-icons/file/file-upload';
import ContentClear from 'material-ui/svg-icons/content/clear';
import getMuiTheme from 'material-ui/styles/getMuiTheme';

describe('ImportButton component', () => {
    const muiTheme = getMuiTheme();
    const getProps = () => {
        return {
            toolbarIcons: {
                box: 'DEFAULT',
                free: 'DEFAULT',
                mapView: 'DEFAULT',
                import: 'DEFAULT',
            },
            mode: 'DRAW_NORMAL',
            updateMode: () => {},
            setImportButtonSelected: () => {},
            setAllButtonsDefault: () => {},
            handleCancel: () => {},
            setImportModalState: () => {},
        }
    }
    it('should display the default icon', () => {
        const props = getProps()
        const wrapper = mount(<ImportButton {...props}/>, {
            context: {muiTheme},
            childContextTypes: {muiTheme: React.PropTypes.object}
        });
        expect(wrapper.find('button')).to.have.length(1);
        expect(wrapper.find('div')).to.have.length(2);
        // const icon = wrapper.find('i')
        // expect(icon).to.have.length(1);
        // expect(icon.text()).to.equal('file_upload')
        // expect(icon.hasClass('material-icons')).to.equal(true);
        // expect(icon.hasClass('defaultButton')).to.equal(true);    
        expect(wrapper.find(FileFileUpload)).to.have.length(1);
        expect(wrapper.find(FileFileUpload).hasClass('defaultButton')).to.be.true;
    });

    it('should display inactive icon based on updated props', () => {
        const props = getProps();
        const wrapper = mount(<ImportButton {...props}/>, {
            context: {muiTheme},
            childContextTypes: {muiTheme: React.PropTypes.object}
        });
        const newProps = {toolbarIcons: {import: 'INACTIVE'}}
        wrapper.setProps(newProps);
        expect(wrapper.find('button')).to.have.length(1);
        expect(wrapper.find('div')).to.have.length(2);
        // const icon = wrapper.find('i')
        // expect(icon).to.have.length(1);
        // expect(icon.text()).to.equal('file_upload')
        // expect(icon.hasClass('material-icons')).to.equal(true);
        // expect(icon.hasClass('inactiveButton')).to.equal(true);    
        expect(wrapper.find(FileFileUpload)).to.have.length(1);
        expect(wrapper.find(FileFileUpload).hasClass('inactiveButton')).to.be.true;
    });

    it('should display selected icon based on updated props', () => {
        const props = getProps();
        const wrapper = mount(<ImportButton {...props}/>, {
            context: {muiTheme},
            childContextTypes: {muiTheme: React.PropTypes.object}
        });
        const newProps = {toolbarIcons: {import: 'SELECTED'}}
        wrapper.setProps(newProps);
        expect(wrapper.find('button')).to.have.length(1);
        expect(wrapper.find('div')).to.have.length(2);
        // const icon = wrapper.find('i')
        // expect(icon).to.have.length(1);
        // expect(icon.text()).to.equal('clear')
        // expect(icon.hasClass('material-icons')).to.equal(true);
        // expect(icon.hasClass('selectedButton')).to.equal(true);    
        expect(wrapper.find(ContentClear)).to.have.length(1);
        expect(wrapper.find(ContentClear).hasClass('selectedButton')).to.be.true;
    });

    it('should execute componentWillReceiveProps when new props are passed in', () => {
        const props = getProps();
        const wrapper = mount(<ImportButton {...props}/>, {
            context: {muiTheme},
            childContextTypes: {muiTheme: React.PropTypes.object}
        });
        const updateSpy = new sinon.spy(ImportButton.prototype, 'componentWillReceiveProps');
        wrapper.setProps(props);
        expect(updateSpy.calledOnce).to.equal(true);
    });

    it('should handleOnClick when icon is in SELECTED state', () => {   
        const props = getProps();
        const wrapper = mount(<ImportButton {...props}/>, {
            context: {muiTheme},
            childContextTypes: {muiTheme: React.PropTypes.object}
        });
        let newProps = getProps();
        newProps.toolbarIcons.import = 'SELECTED';
        newProps.setAllButtonsDefault = sinon.spy();
        newProps.handleCancel = sinon.spy();
        newProps.setImportModalState = sinon.spy();
        wrapper.setProps(newProps);
        wrapper.find('button').simulate('click');
        expect(newProps.setAllButtonsDefault.calledOnce).to.equal(true);
        expect(newProps.setImportModalState.calledOnce).to.equal(true);
        expect(newProps.handleCancel.calledOnce).to.equal(true);
    });

    it('should handleOnClick when icon is in DEFAULT state', () => {
        let props = getProps();
        props.setImportButtonSelected = sinon.spy();
        props.setImportModalState = sinon.spy();
        const wrapper = mount(<ImportButton {...props}/>, {
            context: {muiTheme},
            childContextTypes: {muiTheme: React.PropTypes.object}
        });
        wrapper.find('button').simulate('click');
        expect(props.setImportButtonSelected.calledOnce).to.equal(true);
        expect(props.setImportModalState.calledOnce).to.equal(true);
    });

    it('handleOnClick should do nothing when icon is in INACTIVE state', () => {
        const props = getProps();
        const wrapper = mount(<ImportButton {...props}/>, {
            context: {muiTheme},
            childContextTypes: {muiTheme: React.PropTypes.object}
        });
        let newProps = getProps();
        newProps.toolbarIcons.import = 'INACTIVE';
        newProps.setAllButtonsDefault = sinon.spy();
        newProps.handleCancel = sinon.spy();
        newProps.setImportButtonSelected = sinon.spy();
        newProps.setImportModalState = sinon.spy();
        wrapper.setProps(newProps);
        expect(newProps.setAllButtonsDefault.calledOnce).to.equal(false);
        expect(newProps.handleCancel.calledOnce).to.equal(false);
        expect(newProps.setImportButtonSelected.calledOnce).to.equal(false);
        expect(newProps.setImportModalState.calledOnce).to.equal(false);
    });
});
