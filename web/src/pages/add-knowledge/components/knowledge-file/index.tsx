import ChunkMethodModal from '@/components/chunk-method-modal';
import SvgIcon from '@/components/svg-icon';
import {
  useSelectDocumentList,
  useSetDocumentStatus,
} from '@/hooks/documentHooks';
import { useSetSelectedRecord } from '@/hooks/logicHooks';
import { useSelectParserList } from '@/hooks/userSettingHook';
import { IKnowledgeFile } from '@/interfaces/database/knowledge';
import { getExtension } from '@/utils/documentUtils';
import { Divider, Flex, Switch, Table, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useTranslation } from 'react-i18next';
import CreateFileModal from './create-file-modal';
import WebCrawlModal from './web-crawl-modal';
import DocumentToolbar from './document-toolbar';
import {
  useChangeDocumentParser,
  useCreateEmptyDocument,
  useFetchDocumentListOnMount,
  useGetPagination,
  useGetRowSelection,
  useHandleUploadDocument, useHandleWebCrawl,
  useNavigateToOtherPage,
  useRenameDocument,
} from './hooks';
import ParsingActionCell from './parsing-action-cell';
import ParsingStatusCell from './parsing-status-cell';
import RenameModal from './rename-modal';

import FileUploadModal from '@/components/file-upload-modal';
import { formatDate } from '@/utils/date';
import styles from './index.less';

const { Text } = Typography;

const KnowledgeFile = () => {
  const data = useSelectDocumentList();
  const { fetchDocumentList } = useFetchDocumentListOnMount();
  const parserList = useSelectParserList();
  const { pagination } = useGetPagination(fetchDocumentList);
  const onChangeStatus = useSetDocumentStatus();
  const { toChunk } = useNavigateToOtherPage();
  const { currentRecord, setRecord } = useSetSelectedRecord();
  const {
    renameLoading,
    onRenameOk,
    renameVisible,
    hideRenameModal,
    showRenameModal,
  } = useRenameDocument(currentRecord.id);
  const {
    createLoading,
    onCreateOk,
    createVisible,
    hideCreateModal,
    showCreateModal,
  } = useCreateEmptyDocument();
  const {
    changeParserLoading,
    onChangeParserOk,
    changeParserVisible,
    hideChangeParserModal,
    showChangeParserModal,
  } = useChangeDocumentParser(currentRecord.id);
  const {
    documentUploadVisible,
    hideDocumentUploadModal,
    showDocumentUploadModal,
    onDocumentUploadOk,
    documentUploadLoading,
  } = useHandleUploadDocument();
  const {
    webCrawlUploadVisible,
    hideWebCrawlUploadModal,
    showWebCrawlUploadModal,
    onWebCrawlUploadOk,
    webCrawlUploadLoading,
  } = useHandleWebCrawl();
  const { t } = useTranslation('translation', {
    keyPrefix: 'knowledgeDetails',
  });

  const rowSelection = useGetRowSelection();

  const columns: ColumnsType<IKnowledgeFile> = [
    {
      title: t('name'),
      dataIndex: 'name',
      key: 'name',
      fixed: 'left',
      render: (text: any, { id, thumbnail, name }) => (
        <div className={styles.toChunks} onClick={() => toChunk(id)}>
          <Flex gap={10} align="center">
            {thumbnail ? (
              <img className={styles.img} src={thumbnail} alt="" />
            ) : (
              <SvgIcon
                name={`file-icon/${getExtension(name)}`}
                width={24}
              ></SvgIcon>
            )}
            <Text ellipsis={{ tooltip: text }} className={styles.nameText}>
              {text}
            </Text>
          </Flex>
        </div>
      ),
    },
    {
      title: t('chunkNumber'),
      dataIndex: 'chunk_num',
      key: 'chunk_num',
    },
    {
      title: t('uploadDate'),
      dataIndex: 'create_time',
      key: 'create_time',
      render(value) {
        return formatDate(value);
      },
    },
    {
      title: t('chunkMethod'),
      dataIndex: 'parser_id',
      key: 'parser_id',
      render: (text) => {
        return parserList.find((x) => x.value === text)?.label;
      },
    },
    {
      title: t('enabled'),
      key: 'status',
      dataIndex: 'status',
      render: (_, { status, id }) => (
        <>
          <Switch
            checked={status === '1'}
            onChange={(e) => {
              onChangeStatus(e, id);
            }}
          />
        </>
      ),
    },
    {
      title: t('parsingStatus'),
      dataIndex: 'run',
      key: 'run',
      render: (text, record) => {
        return <ParsingStatusCell record={record}></ParsingStatusCell>;
      },
    },
    {
      title: t('action'),
      key: 'action',
      render: (_, record) => (
        <ParsingActionCell
          setCurrentRecord={setRecord}
          showRenameModal={showRenameModal}
          showChangeParserModal={showChangeParserModal}
          record={record}
        ></ParsingActionCell>
      ),
    },
  ];

  const finalColumns = columns.map((x) => ({
    ...x,
    className: `${styles.column}`,
  }));

  return (
    <div className={styles.datasetWrapper}>
      <h3>{t('dataset')}</h3>
      <p>{t('datasetDescription')}</p>
      <Divider></Divider>
      <DocumentToolbar
        selectedRowKeys={rowSelection.selectedRowKeys as string[]}
        showCreateModal={showCreateModal}
        showWebCrawlModal={showWebCrawlUploadModal}
        showDocumentUploadModal={showDocumentUploadModal}
      ></DocumentToolbar>
      <Table
        rowKey="id"
        columns={finalColumns}
        dataSource={data}
        // loading={loading}
        pagination={pagination}
        rowSelection={rowSelection}
        className={styles.documentTable}
        scroll={{ scrollToFirstRowOnChange: true, x: 1300 }}
      />
      <CreateFileModal
        visible={createVisible}
        hideModal={hideCreateModal}
        loading={createLoading}
        onOk={onCreateOk}
      />
      <ChunkMethodModal
        documentId={currentRecord.id}
        parserId={currentRecord.parser_id}
        parserConfig={currentRecord.parser_config}
        documentExtension={getExtension(currentRecord.name)}
        onOk={onChangeParserOk}
        visible={changeParserVisible}
        hideModal={hideChangeParserModal}
        loading={changeParserLoading}
      />
      <RenameModal
        visible={renameVisible}
        onOk={onRenameOk}
        loading={renameLoading}
        hideModal={hideRenameModal}
        initialName={currentRecord.name}
      ></RenameModal>
      <FileUploadModal
        visible={documentUploadVisible}
        hideModal={hideDocumentUploadModal}
        loading={documentUploadLoading}
        onOk={onDocumentUploadOk}
      ></FileUploadModal>
      <WebCrawlModal
        visible={webCrawlUploadVisible}
        hideModal={hideWebCrawlUploadModal}
        loading={webCrawlUploadLoading}
        onOk={onWebCrawlUploadOk}
      ></WebCrawlModal>
    </div>
  );
};

export default KnowledgeFile;
